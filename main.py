import json,re,requests,schedule,time
from datetime import datetime,timedelta
from tkinter import messagebox
proxies = {'http':None,'https':None}
def get_config():
    config_file_path = 'config.json' # 配置文件路径,默认在同一目录下
    with open(config_file_path,'r',encoding='utf-8') as f:
        config_file = json.load(f)
    config = {}
    config['pushplus token'] = config_file['pushplus token']
    config['remind time'] = config_file['remind time']
    config['room_name'] = config_file['room_name']

    # 不同的宿舍区对应不同的客户端,需区分
    斋区 = {'聚翰斋':'18118','红豆斋':'18120','紫薇斋':'18119','风槐斋':'7395','雨鹃斋':'7603','蓬莱客舍':'17887'}
    北校区 = {'杜衡阁':'73','桃李斋':'58','米兰斋':'56','山茶斋':'54','凌霄斋':'59','银桦斋':'61','海桐斋':'57','红榴斋':'55','文杏阁':'70','海棠阁':'71','辛夷阁':'74','紫藤轩':'77','紫檀轩':'65','石楠轩':'66','芸香阁':'68','云杉轩':'76','韵竹阁':'75','疏影阁':'72','木犀轩':'63','丹枫轩':'64','苏铁轩':'67','丁香阁':'69','乔梧阁 2-10 层':'7724','乔梧阁 11-20 层':'7725','乔森阁 11-20 层':'6876','乔森阁 2-10 层':'6875','乔木阁 1-10 层':'6122','乔木阁 11-12 层':'6364','乔相阁 2-10 层':'6877','乔相阁 11-20 层':'6878','乔林阁 1-10 层':'6121','乔林阁 11-12 层':'6363','留学生公寓':'8147'}
    西丽 = {'栋风信子':'10057','栋山楂树':'10934','栋胡杨林':'10935'}
    南校区 = {'春笛 3-8 楼':'6875','春笛 9-17 楼':'7119','夏筝 3-17 楼':'6876','秋瑟 3-8 楼':'6877','秋瑟 9-17 楼':'7828','冬筑 3-6 楼':'6878','冬筑 7-10 楼':'8240','冬筑 11-14 楼':'8241','冬筑 15-17 楼':'8242'}
    if config_file["room_id"] in 斋区:
        config['client'] = '192.168.84.87'
        config['room_id'] = 斋区[config_file['room_id']]
    elif config_file["room_id"] in 北校区:
        config['client'] = '192.168.84.1'
        config['room_id'] = 北校区[config_file['room_id']]
    elif config_file["room_id"] in 西丽:
        config['client'] = '172.21.101.11'
        config['room_id'] = 西丽[config_file['room_id']]
    elif config_file["room_id"] in 南校区:
        config['client'] = '192.168.84.110'
        config['room_id'] = 南校区[config_file['room_id']]
    return config

def main(config):
    push=''
    now = datetime.now()
    if int(now.strftime('%H')) == 0 and int(now.strftime('%M')) < 17:
        push += ('未到昨日日电量结算时间，查询前日电量:\n')
        now -= timedelta(days=2)
    else:
        push += ('昨日电量已结算，结果如下：\n')
        now -= timedelta(days=1)
    today_date = now.strftime('%Y-%m-%d')
    yesterday_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    post_data = {
    'isHost':'0',
    'beginTime':yesterday_date,
    'endTime':today_date,
    'type':'2',
    'client':config['client'],
    'roomId':config['room_id'],
    'roomName':config['room_name']
    }
    query_url = 'http://192.168.84.3:9090/cgcSims/selectList.do'
    try:
        query_response = requests.post(url=query_url,data=post_data,proxies=proxies,timeout=3)
        flag = 1
    except:
        flag = 0
        push += '未连接至深大内网'
        print('未连接至深大内网')
    if flag == 1: # 网络连接无问题则输出用电数据
        date = re.findall(r'([0-9\-]{10})',query_response.text)[1]
        data = re.findall(r'<td width="13%" align="center">\s*([0-9\.]+)\s*</td>',query_response.text)
        
        # 计算购买的电量
        buy_yesterday = float(data[4])
        buy_today = float(data[9])
        buy = buy_today - buy_yesterday

        if data == []:
            push += '未查询到用电数据'
            print('未查询到用电数据')
        used = round((float(data[2]) - float(data[7])),2) # 因浮点数精度过高，不利于美观地显示数据，故仅保留两位小数
        remaining = data[7]
        push += (f'''
        日期: {date}
        用电量: {used+buy}度
        剩余电量: {remaining}度
        ''')
        print(push)
    try:
        pushplus = requests.get(url = f'http://www.pushplus.plus/send?token={config["pushplus token"]}&title=电量提醒&content={push}&topic=923', proxies = proxies, timeout=3)
        result_code = json.loads(pushplus.text)['code']
        if result_code == 200:
            print('pushplus推送成功, 于微信公众号查看')
        else:
            print(f'pushplus推送失败, 返回状态码{result_code}')
            messagebox.showinfo('结果',push+'\npushplus推送失败\n')
    except:
        print('pushplus推送失败, 检查网络连接')
        messagebox.showinfo('结果',push+'\npushplus推送失败\n')

if __name__=='__main__':
    config = get_config()
    if config['remind time']:
        # 定时提醒功能，于配置文件填入时间，需后台运行
        remind_time = config['remind time']
        schedule.every().day.at(remind_time).do(main,config)
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        # 无定时则开机自启
        main(config)
