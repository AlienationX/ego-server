import requests
import json
import sys
import time
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from loguru import logger

FILE_PATH = sys.path[0]

# 同时将日志输出到屏幕和文件，默认会自动输出到屏幕，只需添加一个文件即可。
# logger.add(sys.stdout, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add(f"{FILE_PATH}/save_data_{date.today()}.log", level="DEBUG",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36",
    "access-key": "xxm123321@#"
}


def save_classify():
    # 接口的pageSize最大好像只支持20
    params = {"pageNum": 1, "pageSize": 20}
    response = requests.get("https://tea.qingnian8.com/api/bizhi/classify", params=params, headers=HEADERS)

    classids = []
    initial_data = []
    if response.status_code == 200:
        data = response.json()
        if data["errCode"] != 0:
            raise Exception(data)

        with open(FILE_PATH + "/classify.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        i = 0
        for row in data["data"]:
            extend_fields = {
                "created_at": str(datetime.now(timezone.utc)),   # 使用带有时区的时间
                "updated_at": str(datetime.now(timezone.utc))
            }
            new_row = {**row, **extend_fields}
            classids.append(new_row["_id"])
            del new_row["updateTime"]

            i = i + 1
            initial_data.append({
                "model": "wallpaper.Classify",
                "pk": i,
                "fields": new_row
            })

            # 下载相应图片
            save_pics("classify_home", new_row["picurl"])

        with open(FILE_PATH + "/initial_classify.json", "w") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)

    else:
        print(f"request classify 状态码错误: {response.status_code} ")
        print(response)

    logger.info(f"{len(classids)} {classids}")
    return classids


def save_wallpaper(classid):
    # 读取initial_classify.json数据，以便查找匹配classify的自增id，写入到wall的class_id中
    with open(FILE_PATH + "/initial_classify.json", "r") as f:
        classify_data = json.load(f)

    # 接口的pageSize最大好像只支持20
    params = {"classid": classid, "pageNum": 1, "pageSize": 20}

    initial_data = []
    i = 0
    while True:
        response = requests.get("https://tea.qingnian8.com/api/bizhi/wallList", params=params, headers=HEADERS)

        if response.status_code == 200:
            data = response.json()
            # with open(FILE_PATH + f"/wall_{classid}_{params['pageNum']}.json", "w") as f:
            #     json.dump(data, f, ensure_ascii=False, indent=4)

            for row in data["data"]:
                extend_fields = {
                    "created_at": str(datetime.now(timezone.utc)),
                    "updated_at": str(datetime.now(timezone.utc)),
                    "is_active": True
                }
                new_row = {**row, **extend_fields}
                new_row["picurl"] = new_row.pop("smallPicurl").replace("_small.webp", ".jpg")  # 只存储大图地址
                new_row["publisher"] = new_row.pop("nickname")
                new_row["tabs_str"] = ",".join(new_row["tabs"])
                new_row["tabs"] = new_row.pop("tabs_str")
                new_row["score"] = None if new_row["score"] == "NaN" else new_row["score"]

                new_row["_classid"] = new_row.pop("classid")
                for classify_row in classify_data:
                    if classify_row["fields"]["_id"] == new_row["_classid"]:
                        new_row["class_id"] = classify_row["pk"]

                i = i + 1
                initial_data.append({
                    "model": "wallpaper.Wall",
                    "pk": i,
                    "fields": new_row
                })

                # 下载相应图片
                save_pics(f"classify_{new_row['class_id']}", new_row["picurl"])

            logger.info(f"{classid} {new_row['class_id']} count: {len(initial_data)} {params['pageNum']}")
            if not data["data"] or len(initial_data) % params["pageSize"] != 0:
                logger.info(f"Save {classid} {len(initial_data)} done.")
                break
            else:
                params["pageNum"] = params["pageNum"] + 1
                time.sleep(5)

        else:
            print(f"request wall 状态码错误: {response.status_code} ")
            print(response)

    # with open(FILE_PATH + f"/initial_wall_{classid}.json", "w") as f:
    #     logger.info(f"Save wall {classid} 数据量 {len(initial_data)}")
    #     json.dump(initial_data, f, ensure_ascii=False, indent=4)

    return initial_data


def save_banner():
    response = requests.get("https://tea.qingnian8.com/api/bizhi/homeBanner", headers=HEADERS)

    initial_data = []
    if response.status_code == 200:
        data = response.json()
        if data["errCode"] != 0:
            raise Exception(data)

        with open(FILE_PATH + "/banner.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        i = 0
        for row in data["data"]:
            extend_fields = {
                "created_at": str(datetime.now(timezone.utc)),   # 使用带有时区的时间
                "enable": True
            }
            new_row = {**row, **extend_fields}
            del new_row["_id"]

            i = i + 1
            initial_data.append({
                "model": "wallpaper.Banner",
                "pk": i,
                "fields": new_row
            })

            # 下载相应图片
            save_pics("banner", new_row["picurl"])

        with open(FILE_PATH + "/initial_banner.json", "w") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)

    else:
        print(f"request banner 状态码错误: {response.status_code} ")
        print(response)


def save_pics(folder, picurl):
    picurls = [picurl, ]
    if "_small.webp" in picurl:
        picurls.append(picurl.replace("_small.webp", ".jpg"))

    for picurl in picurls:
        file_name = picurl.split("/")[-1]
        response = requests.get(picurl, headers=HEADERS)
        pic_data = response.content

        folder_path = FILE_PATH + f"/pics/{folder}"
        p = Path(folder_path)
        p.mkdir(parents=True, exist_ok=True)

        with open(FILE_PATH + f"/pics/{folder}/{file_name}", "wb") as f:
            f.write(pic_data)


if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Start time: {start_time}")

    save_banner()

    initial_wall_data = []
    wall_pk = 0
    classids = save_classify()
    for classid in classids:
        classid_wall_data = save_wallpaper(classid)
        # 重新从1生成pk值
        for row in classid_wall_data:
            wall_pk += 1
            row["pk"] = wall_pk
        initial_wall_data.extend(classid_wall_data)  # 两个列表合并成一个列表

    with open(FILE_PATH + f"/initial_wall.json", "w") as f:
        logger.info(f"Save wall 数据量 {len(initial_wall_data)}")
        json.dump(initial_wall_data, f, ensure_ascii=False, indent=4)

    end_time = datetime.now()
    logger.info(f"End time: {end_time}")
    logger.info(f"Time taken: {end_time - start_time} seconds")

    # # 将生成的文件复制到fixtures/wallpaper目录下
    for obj in ["classify", "wall", "banner"]:
        source = Path(FILE_PATH + f"/initial_{obj}.json")
        destination = Path(FILE_PATH + f"/../fixtures/wallpaper/initial_{obj}.json")
        if destination.exists():
            destination.unlink()
        shutil.copy(source, destination)
