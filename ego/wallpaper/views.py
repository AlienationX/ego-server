import base64
import json
import logging
import random
from math import log
from pathlib import Path

import requests
from django.conf import settings
from django.shortcuts import render
from PIL import Image

from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, resize_image

from .models import Classify, Wall

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "wallpaper/index.html")


def upload(request):
    # GET 请求：渲染上传页面
    if request.method == "GET":
        return render(request, "wallpaper/upload.html")

    # POST 请求：处理上传的文件
    if request.method == "POST":
        # 获取 action 参数
        action = request.POST.get("action")

        # 分类
        classify_objects = Classify.objects.all().filter(enable=True)
        classifies = [obj.name for obj in classify_objects]

        # 如果是预览操作，处理上传的文件
        if action == "preview":
            logger.info(f"FILES: {request.FILES}")
            uploaded_files = request.FILES.getlist("images")

            # 如果没有文件，返回错误信息
            if not uploaded_files:
                data = {"items": [], "msg": "请上传文件", "alert_type": "alert-warning"}
                return render(request, "wallpaper/upload_cards.html", data)

            items = []
            for uploaded_file in uploaded_files:
                # 读取本地文件内容为 base64 编码。智普API只能使用url地址或者base64编码，不能直接使用本地文件
                b64 = base64.b64encode(uploaded_file.read()).decode()
                img_base = f"data:{uploaded_file.content_type};base64,{b64}"

                # 这种方式生成的字符串太长会报错，推荐使用上面的方式
                # img_base = base64.b64encode(uploaded_file.read()).decode("utf-8")

                # 1. 保存文件到服务器临时目录
                new_filename = uploaded_file.name.replace(" ", "_").replace("/", "_")
                picurl_tmp = f"upload_tmp11/{new_filename}"
                save_path_tmp = f"{settings.MEDIA_ROOT}/{picurl_tmp}"
                try:
                    with open(save_path_tmp, "wb+") as f:
                        for chunk in uploaded_file.chunks():
                            f.write(chunk)
                except IOError as e:
                    error_msg = f"{new_filename} 文件保存失败，{e}"
                    data = {"items": [], "msg": error_msg, "alert_type": "alert-warning"}
                    return render(request, "wallpaper/upload_cards.html", data)

                # 0. 生成图片描述、标签、分类
                info = _generate_info_with_llm(img_base)
                if "error" in info:
                    data = {"items": [], "msg": info["error"], "alert_type": "alert-warning"}
                    return render(request, "wallpaper/upload_cards.html", data)

                info["picurl"] = f"{info['pic_path_prefix']}/{new_filename}"
                info["tabs"] = info["tabs"]
                info["tabs_list"] = info["tabs"].split(",")
                info["score"] = round(random.uniform(4, 5), 1)
                info["publisher"] = "Admin"
                info["is_locked"] = False

                original_image = Image.open(save_path_tmp)
                original_width, original_height = original_image.size
                info["filename"] = new_filename
                info["size"] = f"{original_width} x {original_height}"
                info["save_path_tmp"] = save_path_tmp
                info["picurl_tmp"] = img_base if settings.ENV == "dev" else picurl_tmp

                items.append(info)

            logger.info({k: v for k, v in items[0].items() if settings.ENV == "dev" and k not in ("picurl_tmp")})

            data = {"items": items, "classifies": classifies}
            return render(request, "wallpaper/upload_cards.html", data)

        # 如果是保存操作，处理表单数据
        elif action == "save":
            # 获取表单数据
            form_data = request.POST
            filenames = form_data.getlist("filename")
            logger.debug(form_data)

            success_count = 0
            error_count = 0

            for i in range(len(filenames)):
                try:
                    obj = _save_wallpaper(form_data, i)

                    logger.debug(f"保存第 {i + 1} 张图片: {obj.picurl}")
                    success_count += 1
                except Exception:
                    logger.exception(f"保存第 {i + 1} 张图片失败")
                    error_count += 1

            # 返回成功消息（items 为空，清空表单）
            if error_count == 0:
                msg = f"成功保存 {success_count} 条记录"
            else:
                msg = f"成功 {success_count} 条，失败 {error_count} 条"

            data = {"items": [], "msg": msg, "alert_type": "alert-success" if error_count == 0 else "alert-warning"}
            return render(request, "wallpaper/upload_cards.html", data)

        # 其他情况，返回错误
        else:
            return render(request, "wallpaper/upload_cards.html", {"items": [], "msg": "未知的操作类型"})


def _generate_info_with_llm(img_url):
    # exclude 取反 实现 notin 逻辑
    classify_objects = Classify.objects.all().exclude(name__in=("必应每日壁纸", "宝可梦官方壁纸", "宝可梦睡眠"))
    classcfy_name = [obj.name for obj in classify_objects]

    prompt = f"""根据图片内容，回答以下问题：
    1. 用自然柔和的语言，生成图片描述,30字以内。
    2. 生成2到5个中英文标签，用英文逗号分隔，逗号之间不要有空格。
    3. 在以下分类中选择最合适的一个作为图片分类：{", ".join(classcfy_name)}。
    请按照以下 JSON 格式返回分析结果：
    {{
        "description": "报纸纹理的动漫角色，蓝色调，侧身姿态，文字元素点缀",
        "tabs": "海贼王,路飞,anime",
        "classify_name": "动漫二次元"
    }}
    """

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG('ZHIPU_API_KEY')}", "Content-Type": "application/json"}
    data = {
        # glm-4.7-flash 免费，但只能输入文字
        # https://bigmodel.cn/finance-center/resource-package/package-mgmt
        # glm-4.6v-flash 免费，支持图片输入。glm-4.6v 付费，支持图片输入，2026-03-12到期
        "model": "glm-4.6v",  # glm-4.6v-flash、glm-4.6v 付费
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            # "url": "https://cloudcovert-1305175928.cos.ap-guangzhou.myqcloud.com/%E5%9B%BE%E7%89%87grounding.PNG"
                            # "url": img_base
                            "url": img_url
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        # "thinking": {"type": "enabled"},
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        response.raise_for_status()

        result = response.json()
        logging.debug(json.dumps(result, indent=2, ensure_ascii=False))

        content = result["choices"][0]["message"]["content"].strip()
        info = json.loads(content)
        info["tabs"] = info.get("tabs").replace(", ", ",")
        info["pic_path_prefix"] = classify_objects.get(name=info["classify_name"]).pic_path_prefix
        info["classify_id"] = classify_objects.get(name=info["classify_name"]).id

        return info

    except Exception as e:
        logging.exception(f"Unexpected error: \n{e}")
        return {"error": str(e)}


def _save_wallpaper(form_data, i):
    record_picurl = form_data.getlist("picurl")[i]
    pic_path_prefix = form_data.getlist("pic_path_prefix")[i]
    save_path_tmp = form_data.getlist("save_path_tmp")[i]

    # 处理 is_locked：checkbox 未勾选时不会提交，按行索引读取更稳定
    is_locked = form_data.get(f"is_locked_{i}") == "on"

    record = {
        "description": form_data.getlist("description")[i],
        "tabs": form_data.getlist("tabs")[i],
        "score": round(random.uniform(4, 5), 1),
        "publisher": form_data.getlist("publisher")[i],
        "is_active": True,
        "is_locked": is_locked,
        # "created_at": datetime.now(),
        # "updated_at": datetime.now(),
        "classify_id": form_data.getlist("classify_id")[i],
        "remark": "upload",
    }
    logger.debug(record)

    # 重置图片尺寸
    resize_path = resize_image(Path(save_path_tmp), Path(f"{settings.MEDIA_ROOT}/{record_picurl}"))
    logger.debug(f"重置图片尺寸: {pic_path_prefix, resize_path}")

    # 生成缩略图
    generate_thumbs(resize_path)

    # # 上传到 s3
    upload_file_to_s3(resize_path, s3_prefix=f"{pic_path_prefix}/")

    # # 上传到 cos
    upload_file_to_cos(resize_path, cos_prefix=f"{pic_path_prefix}/")

    # 上传到数据库
    obj, created = Wall.objects.get_or_create(
        picurl=record_picurl,
        defaults=record,
    )

    # 更新记录
    if not created:
        for key, value in record.items():
            setattr(obj, key, value)
        obj.save()

    return obj
