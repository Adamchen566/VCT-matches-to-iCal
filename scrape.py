import os
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
from ics import Calendar, Event
from datetime import datetime
from pytz import timezone
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
# from google.oauth2 import service_account

file_path = 'D:/BackUp/self-work/VCT-matches-to-iCal/'

# 要爬取的网页地址
url_vlr = 'https://www.vlr.gg/'
# Valorant Champions Tour 2021
url_2021_Reykjavík = 'https://www.vlr.gg/event/matches/353/valorant-champions-tour-stage-2-masters-reykjav-k/?series_id=all'
url_2021_Berlin = 'https://www.vlr.gg/event/matches/466/valorant-champions-tour-stage-3-masters-berlin/?series_id=all'
url_2021_Berlin_champion = 'https://www.vlr.gg/event/matches/449/valorant-champions-2021/?series_id=all'

# Valorant Champions Tour 2022
url_2022_Reykjavík = 'https://www.vlr.gg/event/matches/926/valorant-champions-tour-stage-1-masters-reykjav-k/?series_id=all'
url_2022_Copenhagen = 'https://www.vlr.gg/event/matches/1014/valorant-champions-tour-stage-2-masters-copenhagen/?series_id=all'
url_2022_istanbul = 'https://www.vlr.gg/event/matches/1015/valorant-champions-2022/?series_id=all'

# Valorant Champions Tour 2023
url_2023_Tokyo = 'https://www.vlr.gg/event/matches/1494/champions-tour-2023-masters-tokyo/?series_id=all'
url_2023_LosAngeles_champion = 'https://www.vlr.gg/event/matches/1657/valorant-champions-2023/?series_id=all'

# Valorant Champions Tour 2024
url_kickoff_cn = 'https://www.vlr.gg/event/matches/1926/champions-tour-2024-china-kickoff/?series_id=all'
url_kickoff_amer = 'https://www.vlr.gg/event/matches/1923/champions-tour-2024-americas-kickoff/?series_id=all'
url_kickoff_pac = 'https://www.vlr.gg/event/matches/1924/champions-tour-2024-pacific-kickoff/?series_id=all'
url_kickoff_emea = 'https://www.vlr.gg/event/matches/1925/champions-tour-2024-emea-kickoff/?series_id=all'
url_master_Madrid = 'https://www.vlr.gg/event/matches/1921/champions-tour-2024-masters-madrid/?series_id=all'

url_state1_cn = 'https://www.vlr.gg/event/matches/2006/champions-tour-2024-china-stage-1/?series_id=3841'
url_state1_amer = 'https://www.vlr.gg/event/matches/2004/champions-tour-2024-americas-stage-1/?series_id=3837'
url_state1_pac = 'https://www.vlr.gg/event/matches/2002/champions-tour-2024-pacific-stage-1/?series_id=3833'
url_state1_emea = 'https://www.vlr.gg/event/matches/1998/champions-tour-2024-emea-stage-1/?series_id=3826'
url_master_shanghai = 'https://www.vlr.gg/event/matches/1999/champions-tour-2024-masters-shanghai/?series_id=all'

url_state2_cn = 'https://www.vlr.gg/event/matches/2096/champions-tour-2024-china-stage-2/?series_id=all'
url_state2_amer = 'https://www.vlr.gg/event/matches/2095/champions-tour-2024-americas-stage-2/?series_id=all'
url_state2_pac = 'https://www.vlr.gg/event/matches/2005/champions-tour-2024-pacific-stage-2/?series_id=all'
url_state2_emea = 'https://www.vlr.gg/event/matches/2094/champions-tour-2024-emea-stage-2/?series_id=all'
url_champion_Seoul = 'https://www.vlr.gg/event/matches/2097/valorant-champions-2024/?series_id=all'

url_wallE_cup = 'https://www.vlr.gg/event/matches/2232/wall-e-cup/?series_id=all'
url_TEN_Invitational = 'https://www.vlr.gg/event/matches/2219/ten-valorant-asia-invitational/?series_id=all'
url_FGC = 'https://www.vlr.gg/event/matches/2234/fgc-invitational-2024/?series_id=all'
url_GCC_Berlin = 'https://www.vlr.gg/event/matches/2124/game-changers-2024-championship-berlin/?series_id=all'
url_SEN_city = 'https://www.vlr.gg/event/matches/2248/sen-city-classic/?series_id=all'
url_GES = 'https://www.vlr.gg/event/matches/2216/gwangju-esports-series-asia-2024/?series_id=all'
url_Asian_Invitational = 'https://www.vlr.gg/event/matches/2228/valorant-radiant-asia-invitational/?series_id=all'
url_RedBull = 'https://www.vlr.gg/event/matches/2171/red-bull-home-ground-5/?series_id=all'
url_ShanghaiMaster = 'https://www.vlr.gg/event/matches/2265/shanghai-esports-masters-2024/?series_id=all'
url_SOOP ='https://www.vlr.gg/event/matches/2225/soop-valorant-league/?series_id=all'
url_SuperB = 'https://www.vlr.gg/event/matches/2289/superb-cup/?series_id=all'
url_Roit1 = 'https://www.vlr.gg/event/matches/2224/riot-games-one-2024/?series_id=all'
url_TXH = 'https://www.vlr.gg/event/matches/2278/tixinha-invitational-by-bonoxs/?series_id=all'

# Valorant Champions Tour 2025
url_2025_kickoff_cn = 'https://www.vlr.gg/event/matches/2275/champions-tour-2025-china-kickoff/?series_id=all'
url_2025_kickoff_amer = 'https://www.vlr.gg/event/matches/2274/champions-tour-2025-americas-kickoff/?series_id=all'
url_2025_kickoff_pac = 'https://www.vlr.gg/event/matches/2277/champions-tour-2025-pacific-kickoff/?series_id=all'
url_2025_kickoff_emea = 'https://www.vlr.gg/event/matches/2276/champions-tour-2025-emea-kickoff/?series_id=all'
url_China_Evolution_Act1 = 'https://www.vlr.gg/event/matches/2339/china-evolution-series-act-1/?series_id=all'
url_master_Bangkok = 'https://www.vlr.gg/event/matches/2281/champions-tour-2025-masters-bangkok/?series_id=all'

url_2025_stage1_cn = 'https://www.vlr.gg/event/matches/2359/champions-tour-2025-china-stage-1'
url_2025_stage1_amer = 'https://www.vlr.gg/event/matches/2347/champions-tour-2025-americas-stage-1'
url_2025_stage1_pac = 'https://www.vlr.gg/event/matches/2379/champions-tour-2025-pacific-stage-1'
url_2025_stage1_emea = 'https://www.vlr.gg/event/matches/2380/champions-tour-2025-emea-stage-1'
url_China_Evolution_Act2 = 'https://www.vlr.gg/event/matches/2450/china-evolution-series-act-2-x-asian-champions-league/?series_id=all'
url_master_Toronto = 'https://www.vlr.gg/event/matches/2282/champions-tour-2025-masters-toronto/?series_id=all'

url_champion_Paris = 'https://www.vlr.gg/event/matches/2283/valorant-champions-2025/?series_id=all'


events_by_year = {
    "2021": {
        "Masters Reykjavik": {"Global": "https://www.vlr.gg/event/matches/353/valorant-champions-tour-stage-2-masters-reykjav-k/?series_id=all"},
        "Masters Berlin": {"Global": "https://www.vlr.gg/event/matches/466/valorant-champions-tour-stage-3-masters-berlin/?series_id=all"},
        "Champions Berlin 2021": {"Global": "https://www.vlr.gg/event/matches/449/valorant-champions-2021/?series_id=all"},
    },
    "2022": {
        "Masters Reykjavik": {"Global": "https://www.vlr.gg/event/matches/926/valorant-champions-tour-stage-1-masters-reykjav-k/?series_id=all"},
        "Masters Copenhagen": {"Global": "https://www.vlr.gg/event/matches/1014/valorant-champions-tour-stage-2-masters-copenhagen/?series_id=all"},
        "Champions istanbul 2022": {"Global": "https://www.vlr.gg/event/matches/1015/valorant-champions-2022/?series_id=all"},
    },
    "2023": {
        "Masters Tokyo": {"Global": "https://www.vlr.gg/event/matches/1494/champions-tour-2023-masters-tokyo/?series_id=all"},
        "Champions 2023": {"Global": "https://www.vlr.gg/event/matches/1657/valorant-champions-2023/?series_id=all"},
    },
    "2024": {
        "Kickoff": {
            "CN": "https://www.vlr.gg/event/matches/1926/champions-tour-2024-china-kickoff/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/1923/champions-tour-2024-americas-kickoff/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/1924/champions-tour-2024-pacific-kickoff/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/1925/champions-tour-2024-emea-kickoff/?series_id=all"
        },
        "Masters Madrid": {
            "Global": "https://www.vlr.gg/event/matches/1921/champions-tour-2024-masters-madrid/?series_id=all"
        },
        "Stage 1": {
            "CN": "https://www.vlr.gg/event/matches/2006/champions-tour-2024-china-stage-1/?series_id=3841",
            "AMER": "https://www.vlr.gg/event/matches/2004/champions-tour-2024-americas-stage-1/?series_id=3837",
            "PAC": "https://www.vlr.gg/event/matches/2002/champions-tour-2024-pacific-stage-1/?series_id=3833",
            "EMEA": "https://www.vlr.gg/event/matches/1998/champions-tour-2024-emea-stage-1/?series_id=3826"
        },
        "Masters Shanghai": {
            "Global": "https://www.vlr.gg/event/matches/1999/champions-tour-2024-masters-shanghai/?series_id=all"
        },
        "Stage 2": {
            "CN": "https://www.vlr.gg/event/matches/2096/champions-tour-2024-china-stage-2/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/2095/champions-tour-2024-americas-stage-2/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/2005/champions-tour-2024-pacific-stage-2/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/2094/champions-tour-2024-emea-stage-2/?series_id=all"
        },
        "Champions Seoul": {
            "Global": "https://www.vlr.gg/event/matches/2097/valorant-champions-2024/?series_id=all"
        }
    },
    "2025": {
        "Evolution Act1": {
            "China": "https://www.vlr.gg/event/matches/2339/china-evolution-series-act-1/?series_id=all",
        },
        "Evolution Act2": {
            "China": "https://www.vlr.gg/event/matches/2450/china-evolution-series-act-2-x-asian-champions-league/?series_id=all",
        },
        "Evolution Act3": {
            "China": ""
        },
        "Kickoff": {
            "CN": "https://www.vlr.gg/event/matches/2275/champions-tour-2025-china-kickoff/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/2274/champions-tour-2025-americas-kickoff/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/2277/champions-tour-2025-pacific-kickoff/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/2276/champions-tour-2025-emea-kickoff/?series_id=all"
        },
        "Masters Bangkok": {
            "Global": "https://www.vlr.gg/event/matches/2281/champions-tour-2025-masters-bangkok/?series_id=all"
        },
        "Stage 1": {
            "CN": "https://www.vlr.gg/event/matches/2359/champions-tour-2025-china-stage-1",
            "AMER": "https://www.vlr.gg/event/matches/2347/champions-tour-2025-americas-stage-1",
            "PAC": "https://www.vlr.gg/event/matches/2379/champions-tour-2025-pacific-stage-1",
            "EMEA": "https://www.vlr.gg/event/matches/2380/champions-tour-2025-emea-stage-1"
        },
        "Masters Toronto": {
            "Global": "https://www.vlr.gg/event/matches/2282/champions-tour-2025-masters-toronto/?series_id=all"
        },
        "Stage 2": {},
        "Champions Paris": {
            "Global": "https://www.vlr.gg/event/matches/2283/valorant-champions-2025/?series_id=all"
        }
    }
}


# 获取比赛详细信息
def get_match_info(url, event, region, isPrint):
    # 发送 GET 请求获取网页内容
    response = requests.get(url)
    # 检查请求是否成功
    if response.status_code == 200:
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        # 在网页上查找比赛时间信息
        date_info = soup.find_all(class_='wf-label mod-large')
        days = -1
        #wrapper > div.col-container > div > div:nth-child(7) > a.wf-module-item.match-item.mod-color.mod-bg-after-purple.mod-first
        #wrapper > div.col-container > div > div:nth-child(5) > a.wf-module-item.match-item.mod-color.mod-bg-after-striped_purple.mod-first
        match_info = soup.select('a.wf-module-item.match-item.mod-color.mod-bg-after-.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-purple.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-purple, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-green.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-green, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-striped_purple.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-striped_purple, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-blue.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-blue, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-red.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-red, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-yellow.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-yellow, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-striped_redyellow.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-striped_redyellow, \
                                 a.wf-module-item.match-item.mod-color.mod-bg-after-orange.mod-first, a.wf-module-item.match-item.mod-color.mod-bg-after-orange')
        # 提取比赛时间信息并输出到控制台
        for info in match_info:
            # 提取比赛日期
            if 'mod-first' in info.attrs['class']:
                days+=1
            date = date_info[days].text.strip()
            if isPrint:print('比赛日期: ', date[:20])
            
            # 提取比赛时间
            time = info.find('div', class_='match-item-time').text.strip()
            if isPrint:print('比赛时间: ', time)

            # 处理时间格式
            cleaned_date = date.split(',')[1].strip()
            date_obj = datetime.strptime(cleaned_date, "%B %d")
            # 修改get_match_info函数中的时间处理部分
            try:
                time_obj = datetime.strptime(time, "%I:%M %p")
                year = int(date.split(',')[2][1:5].strip())
                datetime_combined = date_obj.replace(year=year, hour=time_obj.hour, minute=time_obj.minute)
                formatted_datetime = datetime_combined.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                # 当时间无效时，添加默认的00:00时间
                year = int(date.split(',')[2][1:5].strip())
                datetime_combined = date_obj.replace(year=year, hour=0, minute=0)  # 添加默认时间
                formatted_datetime = datetime_combined.strftime("%Y-%m-%d %H:%M")  # 保持时间格式统一
                time_obj = 'TBD'
            if isPrint:print('日期时间:', formatted_datetime)

            # 提取比赛状态
            status = info.find_all('div', class_='ml-status')
            state = status[0].text
            if state == 'Completed' or state == 'LIVE': # 已完成
                if isPrint:print('Match Completed/Live')

                # 提取队伍名
                teams = info.find_all('div', class_='match-item-vs-team-name')
                team1 = teams[0].text.replace('\n', '').strip()
                team2 = teams[1].text.replace('\n', '').strip()

                # 提取比分
                scores = info.find_all('div', class_='match-item-vs-team-score')
                score1 = scores[0].text.replace('\n', '').strip()
                score2 = scores[1].text.replace('\n', '').strip()

                if isPrint:print(team1, 'vs', team2)
                if isPrint:print(score1, ' : ', score2)
            elif state == 'Upcoming' or state == 'TBD': # 未开赛
                if isPrint:print('Match Upcoming/TBD')

                # 提取队伍名
                teams = info.find_all('div', class_='match-item-vs-team-name')
                team1 = teams[0].text.replace('\n', '').strip()
                team2 = teams[1].text.replace('\n', '').strip()
                # 0:0
                score1 = score2 = 0
                if isPrint:print(team1, 'vs', team2)
                if isPrint:print(score1, ' : ', score2)
            else: # 未发现比赛
                if isPrint:print('Not Found')
            dic = {}
            dic['datetime'] = formatted_datetime
            dic['region'] = region
            dic['team1'] = team1
            dic['team2'] = team2
            dic['score'] = str(score1) + ':' + str(score2)
            event.append(dic)
            if isPrint:print("-------------------------------\n")

        if isPrint:print('比赛数：', len(match_info), '\n\n')
    else:
        if isPrint:print("无法访问该网页")

# 定义排序键函数，根据每个字典中的 'datetime' 键对应的时间进行排序
def sort_key(match):
    try:
        given_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M')
    except ValueError:
        given_time = datetime.strptime(match['datetime'], '%Y-%m-%d')
    return given_time

# 按照格式打印出比赛信息到终端
def matchprint(sorted_event):
    isPassed = 0
    for match in sorted_event:
        try:
            given_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M')
        except ValueError:
            given_time = datetime.strptime(match['datetime'], '%Y-%m-%d')
        current_time = datetime.now()
        # 比较给定时间和当前时间
        if given_time < current_time:
            isPassed = 1
        elif given_time > current_time and isPassed==1:
            print('-'*29 + 'Now' + '-'*74)
            isPassed = 0
        print(f"Datetime: {match['datetime']:<16},  Region: {match['region']:<7}Team: {match['team1']:<20} vs {match['team2']:<22}Score: {match['score']}")

# 找到未来n场比赛信息
def find_next_n_match(n, sorted_event, next_event):
    current_time = datetime.now()
    added = 0
    for match in sorted_event:
        given_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M:%S')
        if given_time > current_time and added<n:
            next_event.append(match)
            added+=1
            current_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M:%S')
        elif added == n:break
    return next_event


# 保存比赛信息
def save2file(event, path, name, title):
    name = path + name
    region_len = len(event[0]['region'])
    # print('type: ', type(region_len), ' len= ', region_len)
    with open(name, 'w', encoding='utf-8') as output:
        output.write(title)
        output.write('\n')
        for match in event:
            match_info = f"Datetime: {match['datetime']},  Region: {match['region']:<{region_len+2}}Team: {match['team1']:<20} vs {match['team2']:<22}Score: {match['score']}\n"
            output.write(match_info)
    print(title + " txt文件已生成")

def create_ics_file(link, matches, name):
    # 创建日历对象
    calendar = Calendar()

    # 设置时区
    sydney_tz = timezone('Australia/Sydney')

    # 添加事件
    for match in matches:
        event = Event()
        
        # Check if time is TBD
        if match['datetime'].upper() == 'TBD' or not match['datetime']:
            # Use a default time (noon in Sydney timezone)
            default_date = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            local_dt = sydney_tz.localize(default_date)
            event.name = f"[TBD] {match['team1']} vs {match['team2']}"
            event_duration = timedelta(hours=1)  # Shorter duration for TBD events
        else:
            try:
                local_dt = sydney_tz.localize(datetime.strptime(match['datetime'], "%Y-%m-%d %H:%M"))
                event.name = f"{match['team1']} vs {match['team2']}"
                
                # 设置比赛的持续时间
                if match['datetime'].startswith('2024-08-24') or match['datetime'].startswith('2024-08-25'):
                    event_duration = timedelta(hours=5)
                else:
                    event_duration = timedelta(hours=3)
            except ValueError:
                # If datetime format is invalid, fall back to TBD handling
                default_date = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
                local_dt = sydney_tz.localize(default_date)
                event.name = f"[Time Invalid] {match['team1']} vs {match['team2']}"
                event_duration = timedelta(hours=1)
        
        event.begin = local_dt
        event.end = local_dt + event_duration
        event.location = match['region'] + ' Score: ' + match['score']
        event.description = f"Score: {match['score']}\nVLR: {link}\n夜莲直播间: https://live.bilibili.com/24160384?live_from=82002&spm_id_from=333.1007.top_right_bar_window_dynamic.content.click"
        calendar.events.add(event)

    # 将日历保存为 .ics 文件
    title = file_path + name +'.ics'
    with open(title, 'w', encoding='utf-8') as f:
        f.writelines(calendar)
    print(name + " ICS文件已生成")

def update_ics_file(url, matches, ics_file_path):
    # 设置时区为悉尼
    sydney_tz = timezone('Australia/Sydney')
    
    # 读取现有的 .ics 文件
    try:
        with open(ics_file_path, 'r', encoding='utf-8') as f:
            calendar = Calendar(f.read())
    except FileNotFoundError:
        # 如果文件不存在，创建一个新的日历对象
        calendar = Calendar()
        print("ICS 文件不存在，已创建新的日历对象")
    

    # 添加新的比赛事件
    for match in matches:
        event_name = f"{match['team1']} vs {match['team2']}"
        local_dt = sydney_tz.localize(datetime.strptime(match['datetime'], "%Y-%m-%d %H:%M"))


        # 如果比赛不存在，创建新事件
        event = Event()
        event.name = event_name
        event.begin = local_dt

        # 设置比赛的持续时间
        if match['datetime'].startswith('2024-08-24') or match['datetime'].startswith('2024-08-25'):
            event_duration = timedelta(hours=5)
        else:
            event_duration = timedelta(hours=3)
        
        event.end = local_dt + event_duration
        event.location = match['region'] + ' Score: ' +match['score']
        event.description = f"Score: {match['score']}\nVLR: {url}\n夜莲直播间: https://live.bilibili.com/24160384?live_from=82002&spm_id_from=333.1007.top_right_bar_window_dynamic.content.click"    

        calendar.events.add(event)

    # 将更新后的日历保存回 .ics 文件
    with open(ics_file_path, 'w', encoding='utf-8') as f:
        f.writelines(calendar)

    print("ICS 文件已更新")

def convert_google_drive_link_to_direct_download(google_drive_link):
    """
    将 Google Drive 共享链接转换为直接下载链接，用于 iPhone 日历订阅
    :param google_drive_link: Google Drive 共享链接
    :return: 直接下载链接
    """
    # 检查链接是否为有效的 Google Drive 链接
    if "drive.google.com" not in google_drive_link:
        raise ValueError("输入的链接不是有效的 Google Drive 共享链接")

    # 提取文件 ID
    try:
        file_id = google_drive_link.split("/d/")[1].split("/")[0]
    except IndexError:
        raise ValueError("无法提取文件 ID，请检查链接格式")

    # 构建直接下载链接
    direct_download_link = f"https://drive.google.com/uc?export=download&id={file_id}"

    print(f"直接下载链接: {direct_download_link}")

    # 指定要保存的文件名
    file_name = "D:\BackUp\self-work\VCT\download_link.txt"

    # 创建并写入文件
    with open(file_name, 'w') as file:
        file.write(direct_download_link)

    print(f"链接已成功导出到 {file_name}")

# 定义函数，将文件上传到 Google Drive
# 已删除原文件并上传新文件
# 但网盘上未更新
# def upload_to_google_drive(file_path, file_name, folder_id=None):
#     # 加载服务账户凭据
#     SCOPES = ['https://www.googleapis.com/auth/drive.file']
#     creds = service_account.Credentials.from_service_account_file('D:\BackUp\self-work\VCT\credentials.json', scopes=SCOPES)
#     service = build('drive', 'v3', credentials=creds)

#     query = f"name='{file_name}'"
#     if folder_id:
#         query += f" and '{folder_id}' in parents"
#     results = service.files().list(q=query, fields="files(id, name)").execute()
#     items = results.get('files', [])
#     for item in items:
#         service.files().delete(fileId=item['id']).execute()
#         print(f"Deleted file: {item['name']} (ID: {item['id']})")

#     # 创建文件元数据
#     file_metadata = {'name': file_name}
#     if folder_id:
#         file_metadata['parents'] = [folder_id]

#     # 上传文件
#     media = MediaFileUpload(file_path, resumable=True)
#     file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
#     print(f"File ID: {file.get('id')} uploaded to Google Drive.")

#     file_info = service.files().get(fileId='https://drive.google.com/file/d/1VnBKxMoCkG2CZaP7Rz_e2Q7uHiwNkVrt/view', fields='name, parents').execute()

#     if 'parents' not in file_info or not file_info['parents']:
#         print(f"文件 '{file_info['name']}' 在根目录 (My Drive)。")
    

# 调用函数获取比赛信息
# 2021
# Reykjavík_2021_event = []
# Berilin_2021_event = []
# Berlin_2021champion_event =[]

# get_match_info(url_2021_Reykjavík, Reykjavík_2021_event, '21Reykjavik', 0)
# get_match_info(url_2021_Berlin, Berilin_2021_event, 'Berlin', 0)
# get_match_info(url_2021_Berlin_champion, Berlin_2021champion_event, '21-Reykjavik-Champion', 0)

# file_name = '/2021 Reykjavik.txt'
# title = 'VCT2021: Master Reykjavik'
# save2file(Reykjavík_2021_event, file_path, file_name, title)

# file_name = '/2021 Berlin.txt'
# title = 'VCT2021: Master Berlin'
# save2file(Berilin_2021_event, file_path, file_name, title)

# file_name = '/2021 Reykjavik Champion.txt'
# title = 'VCT2021: Champion Reykjavik'
# save2file(Berlin_2021champion_event, file_path, file_name, title)


# 2022
# Reykjavík_2022_event = []
# Copenhagen_2022_event = []
# istanbul_2022champion_event = []

# get_match_info(url_2022_Reykjavík, Reykjavík_2022_event, '22 Reykjavik', 0)
# get_match_info(url_2022_Copenhagen, Copenhagen_2022_event, 'Copenhagen', 0)
# get_match_info(url_2022_istanbul, istanbul_2022champion_event, 'istanbul', 0)

# file_name = '/2022 Reykjavik.txt'
# title = 'VCT2022: Master Reykjavik'
# save2file(Reykjavík_2022_event, file_path, file_name, title)

# file_name = '/2022 Copenhagen.txt'
# title = 'VCT2022: Master Copenhagen'
# save2file(Copenhagen_2022_event, file_path, file_name, title)

# file_name = '/2022 istanbul.txt'
# title = 'VCT2022: Champion istanbul'
# save2file(istanbul_2022champion_event, file_path, file_name, title)


# 2023
# Tokyo_2023_event = []
# LosAngeles_2023champion_event = []

# get_match_info(url_2023_Tokyo, Tokyo_2023_event, 'Tokyo', 0)
# get_match_info(url_2023_LosAngeles_champion, LosAngeles_2023champion_event, 'LAchampion', 0)

# file_name = '/2023-Tokyo.txt'
# title = 'VCT2023: Master Tokyo'
# save2file(Tokyo_2023_event, file_path, file_name, title)

# file_name = '/2023-Los Angeles.txt'
# title = 'VCT2023: Champion Los Angeles'
# save2file(Tokyo_2023_event, file_path, file_name, title)


# 2024
# kickoff_event = []
# madrid_event = []
# state1_event = []
# shanghai_event = []
# state2_event = []
# Seoul_event = []
# wallE_event = []
# TEN_Invitational_event = []
# SEN_event = []
# GES_event = []
# FGC_event = []
# GCC_event = []
# Asian_Invitational_event = []
# Red_Bull_event = []
# ShanghaiMaster_event = []
# SOOP_event = []
# SuperB_event = []
# Riot1_event = []
# TXH_event = []



# Kickoff + Madrid
# get_match_info(url_kickoff_cn, kickoff_event, 'CN', 0)
# get_match_info(url_kickoff_amer, kickoff_event, 'AMER', 0)
# get_match_info(url_kickoff_pac, kickoff_event, 'PAC', 0)
# get_match_info(url_kickoff_emea, kickoff_event, 'EMEA', 0)

# sorted_kickoff_event = sorted(kickoff_event, key=sort_key)
# matchprint(sorted_kickoff_event)
# file_name = '/2024-kickoff.txt'
# title = 'VCT2024: Kickoff'
# save2file(sorted_kickoff_event, file_path, file_name, title)

# get_match_info(url_master_Madrid, madrid_event, 'Madrid', 0)
# matchprint(madrid_event)

# file_name = '/2024-Madrid.txt'
# title = 'VCT2024: Master Madrid'
# save2file(madrid_event, file_path, file_name, title)
# print('-'*107)

# # State1 + Shanghai
# get_match_info(url_state1_cn, state1_event, 'CN', 0)
# get_match_info(url_state1_amer, state1_event, 'AMER', 0)
# get_match_info(url_state1_pac, state1_event, 'PAC', 0)
# get_match_info(url_state1_emea, state1_event, 'EMEA', 0)

# sorted_state1_event = sorted(state1_event, key=sort_key)
# matchprint(sorted_state1_event)
# file_name = '/2024-state1.txt'
# title = 'VCT2024: State1'
# save2file(sorted_state1_event, file_path, file_name, title)

# get_match_info(url_master_shanghai, shanghai_event, 'SHN', 0)
# matchprint(shanghai_event)
# file_name = '/2024-ShangHai.txt'
# title = 'VCT2024: Master ShangHai'
# save2file(shanghai_event, file_path, file_name, title)

# # State2 + Seoul
# get_match_info(url_state2_cn, state2_event, 'CN', 0)
# get_match_info(url_state2_amer, state2_event, 'AMER', 0)
# get_match_info(url_state2_pac, state2_event, 'PAC', 0)
# get_match_info(url_state2_emea, state2_event, 'EMEA', 0)

# sorted_state2_event = sorted(state2_event, key=sort_key)
# matchprint(sorted_state2_event)
# file_name = '/2024-state2.txt'
# title = 'VCT2024: State2'
# save2file(sorted_state2_event, file_path, file_name, title)

# get_match_info(url_champion_Seoul, Seoul_event, 'Seoul', 0)
# matchprint(Seoul_event)
# file_name = '/2024-Seoul.txt'
# title = 'VCT2024: Master Seoul'
# save2file(Seoul_event, file_path, file_name, title)

# get_match_info(url_wallE_cup, wallE_event, 'CN', 0)
# matchprint(wallE_event)
# file_name = '/2024-wall-E Cup.txt'
# title = 'VCT2024cn: wall-E Cup'
# save2file(wallE_event, file_path, file_name, title)
# name = '2024-wall-E Cup'
# create_ics_file(wallE_event, file_name)

# get_match_info(url_TEN_Invitational, TEN_Invitational_event, 'TEN', 0)
# get_match_info(url_SEN_city, SEN_event, 'SEN', 0)
# get_match_info(url_GES, GES_event, 'GES', 0)
# get_match_info(url_FGC, FGC_event, 'FGC', 0)
# get_match_info(url_GCC_Berlin, GCC_event, 'GCC', 0)
# get_match_info(url_Asian_Invitational, Asian_Invitational_event, 'Asian', 0)
# get_match_info(url_RedBull, Red_Bull_event, 'RedBull', 0)
# get_match_info(url_ShanghaiMaster, ShanghaiMaster_event, 'S.H Master', 0)
# get_match_info(url_SOOP, SOOP_event, 'SOOP', 0)
# get_match_info(url_SuperB, SuperB_event, 'SuperB', 0)
# get_match_info(url_Roit1, Riot1_event, 'Riot1', 0)
# get_match_info(url_TXH, TXH_event, 'TXH', 0)


# 2025
# kickoff_event = []
evo1_event = []
# Bangkok_event = []
stage1_event = []
evo2_event = []
Toronto_event = []
# state2_event = []
# Paris_event = []

# Kickoff + Bangkok
# get_match_info(url_2025_kickoff_cn, kickoff_event, 'CN', 0)
# get_match_info(url_2025_kickoff_amer, kickoff_event, 'AMER', 0)
# get_match_info(url_2025_kickoff_pac, kickoff_event, 'PAC', 0)
# get_match_info(url_2025_kickoff_emea, kickoff_event, 'EMEA', 0)

# sorted_kickoff_event = sorted(kickoff_event, key=sort_key)
# matchprint(sorted_kickoff_event)

# get_match_info(url_master_Bangkok, Bangkok_event, 'Bangkok', 0)
# matchprint(Bangkok_event)


# Stage1 + Toronto

# get_match_info(url_2025_stage1_cn, stage1_event, 'CN', 0)
# get_match_info(url_2025_stage1_amer, stage1_event, 'AMER', 0)
get_match_info(url_2025_stage1_pac, stage1_event, 'PAC', 0)
get_match_info(url_2025_stage1_emea, stage1_event, 'EMEA', 0)
get_match_info(url_China_Evolution_Act2, evo2_event, 'CN-EVO', 0)
# get_match_info(url_master_Toronto, Toronto_event, 'Toronto', 1)
sorted_stage1_event = sorted(stage1_event + evo2_event + Toronto_event, key=sort_key)

# Stage2 + Paris
# get_match_info(url_champion_Paris, Paris_event, 'Paris', 0)


# OnGoing Events
OnGoing_event = sorted_stage1_event
matchprint(OnGoing_event)
file_name = '/vct OnGoing.txt'
title = 'vct OnGoing'
save2file(OnGoing_event, file_path, file_name, title)
name = 'vct OnGoing'
create_ics_file(url_vlr, OnGoing_event, name)



# Add finished envets to completed ics file
ics_file_path = 'D:\BackUp\self-work\VCT\\vct_completed.ics'
# update_ics_file(url_2021_Reykjavík, Reykjavík_2021_event, ics_file_path)
# update_ics_file(url_2021_Berlin, Berilin_2021_event, ics_file_path)
# update_ics_file(url_2021_Berlin_champion, Berlin_2021champion_event, ics_file_path)

# update_ics_file(url_2022_Reykjavík, Reykjavík_2022_event, ics_file_path)
# update_ics_file(url_2022_Copenhagen, Copenhagen_2022_event, ics_file_path)
# update_ics_file(url_2022_istanbul, istanbul_2022champion_event, ics_file_path)

# update_ics_file(url_2023_Tokyo, Tokyo_2023_event, ics_file_path)
# update_ics_file(url_2023_LosAngeles_champion, LosAngeles_2023champion_event, ics_file_path)

# update_ics_file(url_kickoff_cn, sorted_kickoff_event, ics_file_path)
# update_ics_file(url_master_Madrid, madrid_event, ics_file_path)
# update_ics_file(url_state1_cn, sorted_state1_event, ics_file_path)
# update_ics_file(url_master_shanghai, shanghai_event, ics_file_path)
# update_ics_file(url_state2_cn, sorted_state2_event, ics_file_path)
# update_ics_file(url_champion_Seoul, Seoul_event, ics_file_path)
# update_ics_file(url_wallE_cup, wallE_event, ics_file_path)
# update_ics_file(url_TEN_Invitational, TEN_Invitational_event, ics_file_path)
# update_ics_file(url_SEN_city, SEN_event, ics_file_path)
# update_ics_file(url_GES, GES_event, ics_file_path)
# update_ics_file(url_FGC, FGC_event, ics_file_path)
# update_ics_file(url_Asian_Invitational, Asian_Invitational_event, ics_file_path)
# update_ics_file(url_RedBull, Red_Bull_event, ics_file_path)
# update_ics_file(url_ShanghaiMaster, ShanghaiMaster_event, ics_file_path)
# update_ics_file(url_SOOP, SOOP_event, ics_file_path)
# update_ics_file(url_SuperB, SuperB_event, ics_file_path)
# update_ics_file(url_Roit1, Riot1_event, ics_file_path)
# update_ics_file(url_TXH, TXH_event, ics_file_path)
# update_ics_file(url_2025_kickoff_cn, sorted_kickoff_event, ics_file_path)
# update_ics_file(url_master_Bangkok, Bangkok_event, ics_file_path)


# 示例链接
google_drive_link = "https://drive.google.com/file/d/1VnBKxMoCkG2CZaP7Rz_e2Q7uHiwNkVrt/view?usp=drive_link"

# 调用函数并打印结果
# convert_google_drive_link_to_direct_download(google_drive_link)

# upload_to_google_drive("D:\BackUp\self-work\VCT\\vct OnGoing.ics", "vct OnGoing.ics")


def generate_all_ics():
    from os import makedirs
    from os.path import join

    out_folder = os.path.join(os.path.dirname(__file__), "Calendar_Files")
    makedirs(out_folder, exist_ok=True)

    for year, event_dict in events_by_year.items():
        for event_name, regions in event_dict.items():
            for region, link in regions.items():
                if not link:
                    continue
                print(f"Generating {event_name} ({region})")
                matches = []
                get_match_info(link, matches, region, isPrint=0)
                if matches:
                    filename = f"{year}_{event_name.replace(' ', '_')}_{region}.ics"
                    path = join(out_folder, filename)
                    create_ics_file(link=link, matches=matches, name=filename[:-4])
                    print(f"Saved: {path}")

# 一次生成所有的ics文件
# if __name__ == "__main__":
#     generate_all_ics()