# VLR.gg Valorant 比赛日程工具

[English](README.md) | [简体中文](README.zh.md)

---

## 📖 项目概览

本项目是一个基于 Python 的 **Valorant（无畏契约）比赛数据爬虫与可视化工具**，从 [VLR.gg](https://www.vlr.gg) 抓取数据，支持 `.ics` 日历导出、图形界面多种视图展示，以及多年份多赛区的比赛信息追踪。

订阅日历会**自动发现** vlr.gg 上进行中和即将开始的 VCT 一级赛事，不需要每个赛季手动改配置。覆盖四大赛区的 Kickoff / Stage 1 / Stage 2，以及 Masters 和 Champions：

- Americas（AMER）
- Pacific（PAC）
- EMEA
- China（CN）

GitHub Actions 每天自动更新一次；有比赛即将开始或正在进行时，改为每小时更新，比分和改期会在一小时内同步到日历。

---

## 🎯 功能特色

- **🎮 比赛信息抓取**：抓取比赛名称、时间、参赛队伍和比分。
- **📅 日历导出支持**：将比赛信息转换为 `.ics` 文件，支持日历同步。
- **🖥️ 多视图 GUI 显示**：
  - **表格视图**：结构化完整比赛列表。
  - **卡片视图**：按队伍呈现的紧凑视图。
  - **热力图视图**：各队之间赢下地图数的矩阵。
- **📂 按年份浏览赛事**：直接读取仓库里的日历文件，浏览当前赛事和 2021 年至今的全部归档，离线可用。
- **📱 日历订阅功能**：可在系统日历中订阅 `.ics` 实时更新。
- **🔄 稳定增量更新**：每场比赛使用固定 UID，避免手机日历产生重复事件。

---

## 🖼 图形界面截图

| 表格视图 | 卡片视图 | 热力图视图 |
|---------|----------|------------|
| ![表格视图](images/view_table.png) | ![卡片视图](images/view_card.png) | ![热力图视图](images/view_heatmap.png) |

使用方法：

```bash
python -m pip install -r requirements-gui.txt
python GUI.py
```

图形界面只读取仓库内的 `vct_OnGoing.ics` 和 `Calendar_Files/`，不访问网络；底部的「复制」按钮会复制当前赛事对应的订阅链接。

---

## 📅 日历订阅说明

想实时掌握比赛进展？请订阅以下自动更新的 `.ics` 文件：

- **当前赛事日历（自动跟踪进行中和即将开始的 VCT 赛事）**：

  https://raw.githubusercontent.com/Adamchen566/VCT-matches-to-iCal/main/vct_OnGoing.ics

只想看某个赛区或某支战队？打开 **[订阅页面](https://adamchen566.github.io/VCT-matches-to-iCal/)**，那里有每个赛区、每支战队的独立日历，以及往年赛程的下载。也可以直接使用这些地址：

- 赛区：`https://adamchen566.github.io/VCT-matches-to-iCal/feeds/region/AMER.ics`（把 `AMER` 换成 `PAC`、`EMEA`、`CN` 或 `INTL`，`INTL` 是国际赛）
- 战队：`https://adamchen566.github.io/VCT-matches-to-iCal/feeds/team/paper-rex.ics`（战队名小写、空格换成连字符，完整列表见订阅页面）

日历事件的标题在赛前是 `[CN] A vs B (Bo3)`，有比分后变成 `[CN] A 2:1 B`。不想在标题里看到比分（避免剧透）的话，在 `events.toml` 里设 `score_in_title = false`。

### 订阅方式：

- **Google 日历**：设置 → 添加日历 → 来自 URL → 粘贴上述链接。
- **iOS/macOS 日历**：文件 → 新建日历订阅 → 粘贴链接。
- **小米/Android 系统日历**：安装支持网络 ICS 订阅的同步应用（例如 [ICSx⁵](https://icsx5.bitfire.at/)），添加上述 URL，设置自动同步，然后在系统日历里勾选该日历。请不要直接下载后“导入”，因为一次性导入不会自动更新。

---

## 🚀 快速开始

### 📋 环境要求

- Python 3.11 及以上
- 支持系统：Windows / macOS / Linux

### 📦 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 🔧 安装方式

```bash
git clone https://github.com/Adamchen566/VCT-matches-to-iCal
cd VCT-matches-to-iCal
python update_calendar.py
python update_calendar.py --check
```

生成文件：

- `vct_OnGoing.ics`：手机/电脑日历订阅文件
- `vct_OnGoing.txt`：按澳洲悉尼时间显示的可读赛程
- `data/matches.json`：稳定更新所需的比赛缓存

### 🔁 赛事的跟踪与归档

- **自动发现**：每次运行读取 vlr.gg 的赛事列表，自动跟踪进行中和即将开始的 VCT 一级赛事。VLR 公布赛程后，比赛会自动出现在订阅日历里。
- **自动归档**：一个赛事全部打完、并且最后一场结束满 7 天后，会从订阅日历移出，归档到 `Calendar_Files/`（日历）、`TEXT_Files/`（可读文本）和 `data/archive/`（数据），例如 `2026_Champions_Global.ics`、`2026_Stage_2_CN.ics`。
- **手动添加**：自动发现只认一级赛事。预选赛或第三方赛事可以在 [`events.toml`](events.toml) 里用 `[[events]]` 添加，保留天数和显示时区也在这个文件里改。
- **补归档**：已经结束的赛事可以直接抓取归档：

  ```bash
  python update_calendar.py --archive 2766/valorant-champions-2026
  ```

- **故障告警**：定时更新失败时（VLR 打不开、页面结构变了、抓到的数据不完整）会自动在仓库开一个 Issue，附运行记录和日志；之后某次运行成功会自动关闭它。每次运行还会先解析一个已结束赛事的页面作为探针，用来区分「还没排赛程」和「页面改版导致解析不出来」。

如果某个赛事抓到的场次比上次发布的少，脚本会拒绝覆盖现有日历；确认是 VLR 真的删了比赛时，用 `python update_calendar.py --allow-shrink`。

---

## 📜 协议许可

本项目遵循 MIT 开源协议，详见 [LICENSE](LICENSE)。

---

## 💬 问题反馈与贡献

1. 发现 bug 或提出建议请提 Issue。
2. 欢迎 Fork 项目并提交 Pull Request！

感谢使用本工具！🎉
