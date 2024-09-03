#!/usr/bin/python3
import json
import re
from datetime import datetime, timedelta
from os import path

import sqlite3
import requests

__auther__ = "YoungerKayn"

script_dir = path.dirname(path.abspath(__file__))
config_path = path.join(script_dir, "reminder_config.json")
log_path = path.join(script_dir, "log.db")
dorm_info_path = path.join(script_dir, "dorm_info.json")
proxies = {"http": None, "https": None}

data_re = r'<td width="13%" align="center">\s*([0-9\.\-]+)\s*</td>'
date_re = r'<td width="22%" align="center">\s*([0-9\-]{10})'


def get_config():
    try:
        with open(config_path, "r", encoding="u8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_path} 未填写")
        with open(config_path, "w", encoding="u8") as f:
            f.write("""{
    "宿舍名": "",
    "门牌号": "",
    "pushplus token": "",
    "pushplus topic": ""
}""")
        exit()

    try:
        with open(dorm_info_path, "r", encoding="u8") as f:
            dorm_info = json.load(f)
    except:
        print(f"宿舍信息文件 {dorm_info_path} 未找到")
        exit()

    dorm_areas = ["斋区", "北校区", "西丽", "南校区"]

    for area in dorm_areas:
        if config["宿舍名"] in dorm_info["宿舍名"][area]:
            config["接入点"] = dorm_info["接入点"][area]
            config["宿舍名"] = dorm_info["宿舍名"][area][config["宿舍名"]]
            break
    else:
        print("无效宿舍信息")
        exit()
    return config


def generate_post(config):
    # Generate POST packet
    date_1 = datetime.now()
    date_0 = date_1 - timedelta(days=2)
    begin_time = date_0.strftime("%Y-%m-%d")
    end_time = date_1.strftime("%Y-%m-%d")
    post_data = {
        "isHost": "0",
        "beginTime": begin_time,
        "endTime": end_time,
        "type": "2",
        "client": config["接入点"],
        "roomId": config["宿舍名"],
        "roomName": config["门牌号"]
    }
    return post_data


def electricity_query(post_data):
    # Get usage data
    query_url = f"http://192.168.84.3:9090/cgcSims/selectList.do"
    query_response = requests.post(url=query_url,
                                   data=post_data,
                                   proxies=proxies,
                                   timeout=3)
    return query_response


def write_data(date, used, remaining, charged):
    try:
        conn = sqlite3.connect(log_path)
        cursor = conn.cursor()
        cursor.execute(
            "create table if not exists ele (date date primary key, used real(10), remaining real(10), charged real(10))"
        )

        cursor.execute(
            f"insert into ele (date, used, remaining, charged) values (\"{date}\", \"{used}\", \"{remaining}\", \"{charged}\")"
        )
        conn.commit()
        cursor.close()
        conn.close()
    except:
        print("数据库写入失败")
        pass


def pushplus(pushplus_token, pushplus_topic, title, content):
    try:
        pushplus = requests.get(
            url=
            f"http://www.pushplus.plus/send?token={pushplus_token}&title={title}&content={content}&topic={pushplus_topic}",
            proxies=proxies,
            timeout=3)
        result_code = json.loads(pushplus.text)["code"]
        if result_code == 200:
            print("pushplus success")
            global push_state
            push_state = 0
        else:
            print(f"pushplus failed: {result_code}")
    except:
        print("pushplus failed, no network connection")


def main(config):
    post_data = generate_post(config)
    print(f"Post: {post_data}")

    query_response = electricity_query(post_data)
    print(f"响应码: {query_response}")

    try:
        date = re.findall(date_re, query_response.text)[1]
        data = re.findall(data_re, query_response.text)
        print(f"结果: {data}")
    except:
        print("未查询到用电数据")
        exit()

    charged = round((float(data[9]) - float(data[4])), 2)  # 昨日充电量
    used = round(float(data[2]) - float(data[7]), 2)  # 昨日用电量 - 昨日充电量
    used_today = round((used + charged), 2)  # 昨日用电量
    remaining = round(float(data[7]), 2)  # 剩余电量

    write_data(date, used_today, remaining, charged)

    # 剩余电量不足一天半的用量时提醒
    if remaining <= used_today * 3 / 2:
        title = "电量报告 - 需要充电"
    else:
        title = "电量报告"
    push = (f"""
    {date}
    用电量: {used_today}度
    剩余电量: {remaining}度
    """)
    if charged:
        push += f"购买电量：{charged}度"
    else:
        push += f"昨日未购买电量"
    print(push)

    # pushplus推送
    if config["pushplus token"]:
        pushplus(config["pushplus token"], config["pushplus topic"], title,
                 push)
    else:
        print("no pushplus token")


if __name__ == "__main__":
    main(get_config())
