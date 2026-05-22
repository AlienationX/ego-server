import base64
import json
import logging
import random
import shutil
from pathlib import Path

import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from PIL import Image
from utils.compare_image import get_file_md5, get_file_shape, get_image_content_hash

from wallpaper.management.commands.upload_cos import upload_file_to_cos
from wallpaper.management.commands.upload_s3 import upload_file_to_s3
from wallpaper.management.commands.utils import generate_thumbs, resize_image

from .models import Classify, Wall

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "wallpaper/index.html")


def upload(request):
    if request.method == "GET":
        return render(request, "wallpaper/upload.html")

    # POST 请求：处理上传的文件
    if request.method == "POST":
        # 获取 action 参数
        action = request.POST.get("action")

        # 分类
        classify_objects = Classify.objects.all()
        classifies = [{"id": obj.id, "name": obj.name} for obj in classify_objects]
        classifies.sort(key=lambda x: x["id"])

        # 如果是预览操作，处理上传的文件
        if action == "preview":
            logger.info(f"FILES: {request.FILES}")
            uploaded_files = request.FILES.getlist("images")

            # 如果没有文件，返回错误信息
            if not uploaded_files:
                data = {"items": [], "msg": "请上传文件", "alert_type": "alert-warning"}
                return render(request, "wallpaper/upload_cards.html", data)

            # 获取全局设置
            use_ai = request.POST.get("use_ai") == "on"
            global_classify_id = request.POST.get("global_classify")
            global_score = request.POST.get("global_score", "")
            global_description = request.POST.get("global_description", "")
            global_tags = request.POST.get("global_tags", "")
            global_resize = request.POST.get("global_resize") == "on"
            global_use_uuid = request.POST.get("global_use_uuid") == "on"

            items = []
            for uploaded_file in uploaded_files:
                # 读取本地文件内容为 base64 编码。智普API只能使用url地址或者base64编码，不能直接使用本地文件
                b64 = base64.b64encode(uploaded_file.read()).decode()
                img_base = f"data:{uploaded_file.content_type};base64,{b64}"

                # 这种方式生成的字符串太长会报错，推荐使用上面的方式
                # img_base = base64.b64encode(uploaded_file.read()).decode("utf-8")

                # 1. 保存文件到服务器临时目录
                new_filename = uploaded_file.name.replace(" ", "_").replace("/", "_")
                picurl_tmp = f"wallpaper/upload_tmp/{new_filename}"
                save_path_tmp = f"{settings.MEDIA_ROOT}/{picurl_tmp}"
                try:
                    with open(save_path_tmp, "wb+") as f:
                        for chunk in uploaded_file.chunks():
                            f.write(chunk)
                except IOError as e:
                    error_msg = f"{new_filename} 文件保存失败，{e}"
                    data = {"items": [], "msg": error_msg, "alert_type": "alert-warning"}
                    return render(request, "wallpaper/upload_cards.html", data)

                # 初始化信息字典
                info = {}

                # 根据是否使用AI来生成信息
                if use_ai:
                    # 使用AI生成图片描述、标签、分类
                    ai_info = _generate_info_with_llm(img_base)
                    if "error" in ai_info:
                        data = {"items": [], "msg": ai_info["error"], "alert_type": "alert-warning"}
                        return render(request, "wallpaper/upload_cards.html", data)
                    info.update(ai_info)
                    info["tags_list"] = info["tags"].split(",")
                    info["score"] = round(random.uniform(4, 5), 1)
                    info["resize"] = True
                    info["use_uuid"] = True
                else:
                    # 使用全局设置
                    info["description"] = global_description
                    info["tags"] = global_tags
                    info["tags_list"] = global_tags.split(",") if global_tags else []
                    info["score"] = float(global_score) if global_score else round(random.uniform(4, 5), 1)
                    info["classify_id"] = int(global_classify_id) if global_classify_id else ""
                    info["resize"] = global_resize
                    info["use_uuid"] = global_use_uuid

                info["publisher"] = "Admin"
                info["is_locked"] = False

                original_image = Image.open(save_path_tmp)
                original_width, original_height = original_image.size
                info["filename"] = new_filename
                info["size"] = f"{original_width} x {original_height}"
                info["save_path_tmp"] = save_path_tmp
                # info["picurl_tmp"] = img_base if settings.ENV == "dev" else f"{settings.NGINX_MEDIA_URL}/{picurl_tmp}"
                info["picurl_tmp"] = img_base

                items.append(info)

            logger.info({k: v for k, v in items[0].items() if settings.ENV == "dev" and k not in ("picurl_tmp")})

            data = {"items": items, "classifies": classifies}
            cards_html = render_to_string("wallpaper/upload_cards.html", data, request=request)

            global_form_html = ""
            if not use_ai:
                global_form_html = render_to_string(
                    "wallpaper/upload_global_form.html", {"classifies": classifies}, request=request
                )

            response = HttpResponse(cards_html + global_form_html)
            return response

        # 如果是保存操作，处理表单数据
        elif action == "save":
            form_data = request.POST
            filenames = form_data.getlist("filename")
            logger.debug(form_data)

            success_count = 0
            error_count = 0
            update_count = 0

            for i in range(len(filenames)):
                try:
                    obj, created = _save_wallpaper(form_data, i)

                    logger.debug(f"保存第 {i + 1} 张图片: {obj.picurl}")
                    success_count += 1
                    update_count += 1 if not created else 0
                except Exception:
                    logger.exception(f"保存第 {i + 1} 张图片失败")
                    error_count += 1

            # 返回成功消息（items 为空，清空表单）
            msg = ""
            if success_count > 0:
                msg += f"成功 {success_count} 条记录{f'（包括更新 {update_count} 条记录）' if update_count > 0 else ''}。"
            if error_count > 0:
                msg += f"失败 {error_count} 条记录。"

            data = {"items": [], "msg": msg, "alert_type": "alert-success" if error_count == 0 else "alert-warning"}
            return render(request, "wallpaper/upload_cards.html", data)

        # 其他情况，返回错误
        else:
            return render(request, "wallpaper/upload_cards.html", {"items": [], "msg": "未知的操作类型"})


def _generate_info_with_llm(img_url):
    # exclude 取反 实现 notin 逻辑
    classify_objects = Classify.objects.all().exclude(name__in=("必应每日壁纸", "宝可梦睡眠"))
    classcfy_name = [obj.name for obj in classify_objects]

    prompt = f"""根据图片内容，回答以下问题：
    1. 用自然柔和的语言，生成图片描述，如果识别出图片中的人物，需要包含人物的名称。30字以内。
    2. 生成3到6个中英文标签，用英文逗号分隔，逗号之间不要有空格。
    3. 在以下分类中选择最合适的一个作为图片分类：{", ".join(classcfy_name)}。
    请按照以下 JSON 格式返回分析结果（不要有任何样式或格式化）：
    {{
        "description": "报纸纹理的动漫角色，蓝色调，侧身姿态，文字元素点缀",
        "tags": "海贼王,路飞,anime",
        "classify_name": "动漫二次元"
    }}
    """

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG('ZHIPU_API_KEY')}", "Content-Type": "application/json"}
    data = {
        # glm-4.7-flash 免费，但只能输入文字
        # https://bigmodel.cn/finance-center/resource-package/package-mgmt
        # glm-4.6v-flash 免费，支持图片输入。glm-4.6v 付费，支持图片输入，2026-03-12到期
        "model": "glm-4.6v-flash",
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
        response = requests.post(url, headers=headers, json=data, timeout=60)
        # 不使用 raise_for_status()，方法会在 HTTP 状态码为 4xx 或 5xx 时抛出异常
        # response.raise_for_status()

        # 避免 429 错误抛出异常，显示业务错误信息 https://docs.bigmodel.cn/cn/faq/api-code
        if response.status_code != 200:
            # 返回 API 的原始错误信息
            # {'error': {'code': '1305', 'message': '该模型当前访问量过大，请您稍后再试'}}
            error_data = response.json()
            return error_data

        result = response.json()
        logger.debug(json.dumps(result, indent=2, ensure_ascii=False))

        content = result["choices"][0]["message"]["content"].strip()
        info = json.loads(content)
        info["tags"] = info.get("tags").replace(", ", ",")
        info["classify_id"] = classify_objects.get(name=info["classify_name"]).id

        return info

    except Exception as e:
        logger.exception(f"Unexpected error: \n{e}")
        return {"error": str(e)}


def _save_wallpaper(form_data, i):
    save_path_tmp = form_data.getlist("save_path_tmp")[i]
    classify_id = form_data.getlist("classify_id")[i]
    filename = form_data.getlist("filename")[i]

    pic_path_prefix = Classify.objects.get(id=classify_id).pic_path_prefix
    record_picurl = f"{pic_path_prefix}/{filename}"

    # 处理 is_locked：checkbox 未勾选时不会提交，按行索引读取更稳定
    is_locked = form_data.get(f"is_locked_{i}") == "on"

    # 处理 resize：checkbox 未勾选时不会提交，按行索引读取更稳定
    resize = form_data.get(f"resize_{i}") == "on"

    # 重置图片尺寸或直接复制
    file_path = Path(f"{settings.MEDIA_ROOT}/wallpaper/{record_picurl}")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if resize:
        # 勾选了重置尺寸，调用 resize_image
        resize_path = resize_image(Path(save_path_tmp), file_path)
        logger.debug(f"重置图片尺寸: {pic_path_prefix, resize_path}")
    else:
        # 未勾选重置尺寸，直接复制文件
        shutil.copy2(save_path_tmp, file_path)
        resize_path = file_path
        logger.debug(f"直接复制文件: {pic_path_prefix, resize_path}")

    # 生成缩略图
    # 生成 small 缩略图
    output_file = resize_path.with_name(f"{resize_path.stem}_small.webp")
    generate_thumbs(resize_path, max_size=(520, 520), output_file=output_file)
    # 生成 medium 缩略图
    output_file = resize_path.with_name(f"{resize_path.stem}_medium.webp")
    generate_thumbs(resize_path, max_size=(1024, 1024), output_file=output_file)

    # # 上传到 s3
    # upload_file_to_s3(resize_path, s3_prefix=f"{pic_path_prefix}/")

    # # 上传到 cos
    # upload_file_to_cos(resize_path, cos_prefix=f"{pic_path_prefix}/")

    md5_hash = get_file_md5(file_path)
    content_hash = get_image_content_hash(file_path)
    width, height = get_file_shape(file_path)

    record = {
        "description": form_data.getlist("description")[i],
        "tags": form_data.getlist("tags")[i],
        "score": form_data.getlist("score")[i],
        "publisher": form_data.getlist("publisher")[i],
        "is_active": True,
        "is_locked": is_locked,
        "md5_hash": md5_hash,
        "content_hash": content_hash,
        # "created_at": datetime.now(),
        # "updated_at": datetime.now(),
        "classify_id": classify_id,
        "remark": "upload",
        "width": width,
        "height": height,
    }
    logger.debug(record)

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

    return obj, created
