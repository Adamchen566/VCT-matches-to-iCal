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