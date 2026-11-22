# VCT 比赛数据集

从 [vlr.gg](https://www.vlr.gg) 的比赛页面解析出来的 CSV，由仓库根目录的 `vlr_stats.py` 生成。UTF-8 编码，逗号分隔，空单元格表示页面上没有这项数据。

```bash
python vlr_stats.py events    # 从 VLR 的年度页面列出赛事 -> events.csv
python vlr_stats.py crawl     # 下载比赛页面到 .cache/vlr/（不提交，可重建）
python vlr_stats.py build     # 把缓存解析成下面这些表
python vlr_stats.py check     # 检查各年数据的完整程度
python analyze_stats.py       # 生成 summary/ 里的汇总表
```

`crawl` 默认抓国际赛、联赛和资格赛，每秒一个请求，中断后重跑会从断点继续。加 `--tier challengers` 可以继续抓 2021 到 2022 年的地区 Challengers。

## 目录

```text
data/stats/
├── events.csv            # 赛事目录
├── teams.csv             # 战队索引
├── players.csv           # 选手索引
├── <年份>/
│   ├── matches.csv       # 一行一场比赛
│   ├── vetoes.csv        # 一行一步禁选
│   ├── maps.csv          # 一行一张图
│   ├── rounds.csv        # 一行一个回合
│   └── player_stats.csv  # 一行一位选手在一张图上的数据
└── summary/              # 汇总表，每张表按年份分块，另有 year=all
```

年份是赛事所属的赛季，不是比赛日期所在的年份。

## 表之间怎么连

| 键 | 含义 | 出现在 |
|---|---|---|
| `event_id` | VLR 的赛事编号 | events、matches |
| `match_id` | VLR 的比赛编号（一个 Bo3 或 Bo5） | matches、vetoes、maps、player_stats |
| `game_id` | VLR 的单图编号 | maps、rounds、player_stats |
| `team_id` | VLR 的战队编号，改名后不变 | matches、player_stats、teams |
| `player_id` | VLR 的选手编号，改名和转会后不变 | player_stats、players |

很多列用 `1` 或 `2` 指代战队：`1` 是 `matches.csv` 里的 `team1`，`2` 是 `team2`。

## 各表的列

### events.csv

| 列 | 含义 |
|---|---|
| `year` | 赛季 |
| `tier` | `international`（Masters、Champions、LOCK//IN）、`league`（四大赛区联赛）、`qualifier`（LCQ 等资格赛）、`challengers`（2021 到 2022 年的地区赛） |
| `region` | `AMER`、`EMEA`、`PAC`、`CN`、`INTL`，由赛事名推断，认不出时为空 |
| `name`、`slug`、`status` | VLR 上的赛事名、网址里的名字、状态 |

### matches.csv

| 列 | 含义 |
|---|---|
| `series` | 阶段，例如 `Playoffs: Grand Final` |
| `start_utc` | 开始时间，UTC |
| `patch` | 游戏版本号 |
| `best_of` | 赛制，3 表示 Bo3 |
| `team1_id`、`team1`、`team1_tag` | 战队编号、当时的队名、缩写（`team2` 同理） |
| `score1`、`score2`、`winner` | 大比分和胜方（`1` 或 `2`） |
| `url` | VLR 上的比赛页面 |

### vetoes.csv

| 列 | 含义 |
|---|---|
| `step` | 第几步 |
| `team`、`team_tag` | 哪支战队（`1` 或 `2`）和页面上写的缩写；`remains` 这一步为空 |
| `action` | `ban`、`pick` 或 `remains`（剩下的决胜图） |
| `map` | 地图 |

### maps.csv

| 列 | 含义 |
|---|---|
| `map_no` | 这场比赛的第几张图 |
| `picked_by` | 谁选的图（`1` 或 `2`），决胜图为空 |
| `duration` | 时长，分:秒 |
| `score1`、`score2`、`winner` | 这张图的回合比分和胜方 |
| `team1_atk`、`team1_def`、`team1_ot` | 战队一在进攻方、防守方、加时赢下的回合数（`team2` 同理） |
| `team1_comp`、`team2_comp` | 阵容：五个特工按字母排序，用 `\|` 分隔 |

没有打的图不在表里。

### rounds.csv

| 列 | 含义 |
|---|---|
| `round` | 第几回合 |
| `winner`、`winner_side` | 胜方（`1` 或 `2`）和它当时是进攻方 `atk` 还是防守方 `def` |
| `win_type` | `elimination`（全歼）、`detonation`（炸弹爆炸）、`defuse`（拆包）、`time`（超时） |
| `team1_buy`、`team2_buy` | 经济类型：`pistol`（手枪局）、`eco`（装备不到 10k）、`half`（10k 到 18k）、`full`（18k 以上） |
| `team1_loadout`、`team2_loadout` | 全队装备价值 |
| `team1_bank`、`team2_bank` | 买完之后剩下的钱 |

经济数据只在它和回合胜负逐回合对得上时才填。VLR 的经济页只画前 24 回合，所以加时回合的经济列为空。

### player_stats.csv

| 列 | 含义 |
|---|---|
| `team`、`team_id`、`team_tag` | 所在战队（`1` 或 `2`）、编号、缩写 |
| `player_id`、`player`、`country` | 选手编号、当时的名字、国家或地区 |
| `agent` | 特工 |
| `rating` | VLR 评分 |
| `acs` | 平均战斗得分 |
| `kills`、`deaths`、`assists` | 击杀、死亡、助攻 |
| `kast` | 有击杀、助攻、存活或被换掉的回合占比，百分数 |
| `adr` | 每回合伤害 |
| `hs` | 爆头率，百分数 |
| `fk`、`fd` | 首杀、首死 |
| `k2` 到 `k5` | 双杀到五杀的次数 |
| `clutch_1v1` 到 `clutch_1v5` | 一对多残局获胜的次数 |
| `econ` | 经济评分（每花 1000 造成的伤害） |
| `plants`、`defuses` | 下包和拆包次数 |

从 `rating` 到 `fd` 的每一列都有三份：不带后缀的是整张图，`_atk` 是进攻方半场，`_def` 是防守方半场。

### teams.csv 和 players.csv

战队和选手的索引：最近使用的名字、用过的其他名字、第一场和最后一场的时间、打过的图数。`players.csv` 的 `teams` 是按时间先后待过的战队，`top_agents` 是用得最多的三个特工。

## 汇总表（summary/）

比率都是 0 到 1 的小数。选手的平均值按每张图的回合数加权。

| 表 | 一行是什么 | 主要的列 |
|---|---|---|
| `maps.csv` | 一张地图 | 出场次数、被选率、被禁率、进攻方回合占比、选图方胜率、加时率 |
| `agents.csv` | 一个特工 | 出场率（占全部「战队 × 地图」的比例）、胜率、平均评分和 ACS |
| `agents_by_map.csv` | 一个特工在一张地图上 | 出场率、胜率（少于 5 次的不列） |
| `agents_by_region.csv` | 一个特工在一个赛区 | 出场率、胜率 |
| `comps.csv` | 一套阵容在一张地图上 | 次数、胜率、用过它的战队数（少于 3 次的不列） |
| `players.csv` | 一位选手 | 图数、评分（含攻防）、ACS、KD、KAST、ADR、爆头率、首杀、多杀（三杀及以上）、残局、常用特工 |
| `teams.csv` | 一支战队 | 比赛和地图胜率、回合胜率（含攻防）、手枪局胜率、自选图胜率 |
| `team_maps.csv` | 一支战队在一张地图上 | 场次、胜率、选和禁的次数 |
| `economy.csv` | 一种经济类型对另一种 | 回合数、胜率 |

## 没有的东西

- 选手之间的对位击杀（谁杀了谁几次）在下载的页面里，但没有解析成表。
- 2021 到 2022 年的地区 Challengers 默认不抓。
- 中国赛区和在上海举办的 2024 Masters 是在国服打的，VLR 上缺评分、多杀、残局和经济数据：2024 年这些赛事全部缺，2025 和 2026 年评分大部分有，多杀、残局和经济仍然没有。比较选手评分时要注意这一点。
- 数据以 VLR 当前显示的为准。VLR 会追溯修改队名，所以早年比赛里的队名可能是现在的名字。
