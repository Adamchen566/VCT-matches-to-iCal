# VLR.gg Valorant Match Scraper

[English](README.md) | [简体中文](README.zh.md)


## 项目简介

### 该项目是一个Python爬虫工具，用于从VLR.gg网站爬取Valorant游戏的比赛信息，包括

- 赛事名称

- 比赛日期和时间

- 参赛队伍

- 比赛比分

#### 爬取到的数据将被存储为列表，并经过整理和排序后转换为iCal (.ics) 文件以便导入至日历应用

### 当前版本的程序需要手动上传生成的iCal文件到Google Drive，获取订阅链接后才能在iPhone上订阅。自动上传至云端的功能尚未完成

##### 环境要求:
```
Python 3.x
```

##### 依赖库：


```
requests

BeautifulSoup4

ics
```


### 安装步骤

##### 克隆本项目或下载源码：


```
git clone https://github.com/your-repo/vlr-gg-scraper.git
cd vlr-gg-scraper
```


##### 安装依赖：


```
pip install -r requirements.txt
```


### 使用方法

##### 运行爬虫脚本：


```
python scraper.py
```


##### 生成的 .ics 文件将保存在本地目录。

##### 手动上传 .ics 文件到 Google Drive，并获取共享链接。

##### 在 iPhone 上订阅该日历：

> 打开 设置 > 日历 > 账户 > 添加账户 > 其他 > 添加订阅日历 > 输入共享链接，完成订阅。

## 未来改进

- 实现文件自动上传至云盘

- 根据要求定时更新

- 图形界面/软件


## 许可证

本项目遵循 MIT 许可证，欢迎自由使用和修改。

如果有任何建议或问题，欢迎提交 Issue 或 PR