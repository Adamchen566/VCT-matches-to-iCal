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
from links import *

file_path = os.path.dirname(__file__) + os.sep

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

def generate_all_txt():
    from os import makedirs
    from os.path import join

    out_folder = os.path.join(os.path.dirname(__file__), "TEXT_Files")
    makedirs(out_folder, exist_ok=True)

    for year, event_dict in events_by_year.items():
        for event_name, regions in event_dict.items():
            for region, link in regions.items():
                if not link:
                    continue
                print(f"Generating TXT for {event_name} ({region})")
                matches = []
                get_match_info(link, matches, region, isPrint=0)
                if matches:
                    filename = f"{year}_{event_name.replace(' ', '_')}_{region}.txt"
                    path = join(out_folder, filename)
                    title = f"{year} {event_name} ({region})"
                    save2file(matches, path=out_folder + os.sep, name=filename, title=title)

# 2025
# kickoff_event = []
# evo1_event = []
# Bangkok_event = []
stage1_event = []
evo2_event = []
ACL_event = []
ewc_event = []
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
# get_match_info(url_2025_stage1_pac, stage1_event, 'PAC', 0)
# get_match_info(url_2025_stage1_emea, stage1_event, 'EMEA', 0)
# get_match_info(url_China_Evolution_Act2, evo2_event, 'CN-EVO', 0)
# get_match_info(url_Asian_Champions_League, ACL_event, 'Asian-ACL', 0)
get_match_info(url_ewc, ewc_event, 'EWC', 0)
get_match_info(url_master_Toronto, Toronto_event, 'Toronto', 1)
sorted_stage1_event = sorted(ewc_event, key=sort_key)
get_match_info(url_2025_stage1_cn, stage1_event, 'CN', 0)
get_match_info(url_2025_stage1_amer, stage1_event, 'AMER', 0)
get_match_info(url_2025_stage1_pac, stage1_event, 'PAC', 0)
get_match_info(url_2025_stage1_emea, stage1_event, 'EMEA', 0)
get_match_info(url_China_Evolution_Act2, evo2_event, 'CN-EVO', 0)
get_match_info(url_Asian_Champions_League, ACL_event, 'Asian-ACL', 0)
# get_match_info(url_ewc, ewc_event, 'EWC', 0)
# get_match_info(url_master_Toronto, Toronto_event, 'Toronto', 1)
sorted_stage1_event = sorted(stage1_event + ACL_event + evo2_event, key=sort_key)

# Stage2 + Paris
# get_match_info(url_champion_Paris, Paris_event, 'Paris', 0)


# OnGoing Events
OnGoing_event = sorted_stage1_event
matchprint(OnGoing_event)
file_name = '/vct_OnGoing.txt'
title = 'vct_OnGoing'
save2file(OnGoing_event, file_path, file_name, title)
name = 'vct_OnGoing'
create_ics_file(url_vlr, OnGoing_event, name)


# Add finished envets to completed ics file
ics_file_path = 'D:\BackUp\self-work\VCT-matches-to-iCal\Calendar_Files\\vct_completed.ics'
update_ics_file(url_2025_stage1_cn, stage1_event, ics_file_path)
update_ics_file(url_China_Evolution_Act2, evo2_event, ics_file_path)
update_ics_file(url_Asian_Champions_League, ACL_event, ics_file_path)

# 一次生成所有的文件
if __name__ == "__main__":
    # generate_all_ics()
    # generate_all_txt()
    print("init function")
