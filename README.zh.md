# VLR.gg 瓦洛兰特比赛爬虫

[English](README.md) | [简体中文](README.zh.md)

---

## 📖 项目简介

本项目是一个基于 Python 的爬虫工具，用于从 [VLR.gg](https://www.vlr.gg) 网站爬取 ​**Valorant** 比赛的详细信息。爬取的数据经过整理后生成 `.ics` 文件，方便用户导入日历应用，随时跟踪比赛日程。

### 🎯 功能特性

- ​**🎮 比赛信息爬取**：包括赛事名称、比赛时间、参赛队伍和比分。
- ​**📅 日历文件生成**：将爬取的数据转换为 `.ics` 文件，支持导入 Google Calendar、Apple Calendar 等。
- ​**⚙️ 轻量化设计**：仅依赖少量 Python 库，运行高效。
- ​**📱 跨平台支持**：生成的 `.ics` 文件兼容主流日历应用。

---

## 🚀 快速开始

### 📋 环境要求

- ​**Python 3.x**
- 支持的平台：Windows / macOS / Linux

### 📦 依赖库

```plaintext
requests
BeautifulSoup4
ics
```

### 🔧 安装步骤

​**克隆项目或下载源码**：

   ```bash
   git clone https://github.com/Adamchen566/VCT-matches-to-iCal
   cd vlr-gg-scraper
   ```

## 🛠️ 使用方法

1. **​获取 .ics 文件**:
    - 脚本运行后，生成的 .ics 文件将保存在当前目录。

2. **手动上传至 Google Drive**:
    - 将 .ics 文件上传至 Google Drive，并获取共享链接。

3. **订阅日历**:
    - iPhone：打开 设置 > 日历 > 账户 > 添加账户 > 其他 > 添加 订阅日历，输入共享链接即可。
    - Google Calendar：通过 设置 > 导入日历 上传 .ics 文件。

## 🚧 未来改进

### ☁️ 自动上传云盘

- 实现 `.ics` 文件自动上传至 Google Drive 或 OneDrive，减少手动操作。

### ⏰ 定时更新

- 支持定时爬取和更新比赛信息，确保日历数据实时同步。

### 🖥️ 图形界面

- 开发图形化界面或桌面应用程序，提升用户体验，方便非技术用户使用。

---

## 📜 许可证

本项目遵循 ​**MIT 许可证**，欢迎自由使用、修改和分发。详细信息请参阅 [LICENSE](LICENSE) 文件。

---

## 💬 反馈与贡献

### 提交 Issue

如果您发现任何问题或有改进建议，欢迎提交 [Issue](https://github.com/Adamchen566/VCT-matches-to-iCal/issues)。

### 发起 Pull Request

如果您希望贡献代码或文档，请按照以下步骤操作：

1. Fork 本项目。
2. 创建新的分支 (`git checkout -b feature/YourFeatureName`)。
3. 提交更改 (`git commit -m 'Add some feature'`)。
4. 推送到分支 (`git push origin feature/YourFeatureName`)。
5. 发起 [Pull Request](https://github.com/your-repo/vlr-gg-scraper/pulls)。

您的贡献将帮助本项目变得更好！

---

## 感谢使用！🎉

---