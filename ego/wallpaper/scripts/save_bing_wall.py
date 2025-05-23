import requests
import json
import sys
import os

FILE_PATH = sys.path[0]
BING_PATH = f"{FILE_PATH}/pics/classify_bing/"
DATA_FILE = f"{BING_PATH}/bing_daily_data.json"

# bing_daily_data.json数据，以便查找匹配数据是否存在，不存在则追加
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        bing_daily_data = json.load(f)
else:
    bing_daily_data = []

# 请求API数据: https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN
# 参数说明
# format：返回格式，js 表示JSON，xml 表示XML。
# idx：起始索引（0表示当天，1表示前一天，最多7天前的数据）。
# n：返回的图片数量（最大值为8）。
# mkt：区域代码（例如 zh-CN 为中国，en-US 为美国，不同地区可能返回不同图片）(en-US设置无效，和ip有关)。
params = {
    "format": "js",
    "idx": 0,
    "n": 8,
    "mkt": "zh_CN"
}
api_url = "https://www.bing.com/HPImageArchive.aspx"
response = requests.get(api_url, params=params)
# data = json.loads(response.text)
data = response.json()


for image in data["images"]:
    file_name = image["enddate"] + "-" + image["title"]
    # 解析并拼接图片URL
    image_url = "https://www.bing.com" + image["url"]
    # image_url = image_url.replace("1920x1080", "UHD")  # 改为超高清分辨率
    image_url = image_url.replace("1920x1080", "1080x1920")  # 改为手机分辨率

    # 下载图片
    image_data = requests.get(image_url).content
    with open(f"{BING_PATH}/{file_name}.jpg", "wb") as f:
        f.write(image_data)
    print(f"Save {file_name}.jpg")

    # 保存数据
    new_data = {
        "date": image["enddate"],
        "title": image["title"],
        "description": image["copyright"],
        "url": image_url
    }

    # 判断日数据是否存在，不存在则追加
    if image["enddate"] not in [row["date"] for row in bing_daily_data]:
        bing_daily_data.append(new_data)

# bing_daily_data 排序，并重新降序存储
sorted_bing_daily_data = sorted(bing_daily_data, key=lambda x: x["date"], reverse=True)
with open(DATA_FILE, "w") as f:
    json.dump(sorted_bing_daily_data, f, ensure_ascii=False, indent=4)
    print(f"Save bing_daily_data.json")
