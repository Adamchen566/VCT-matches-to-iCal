# VLR.gg Valorant Match Scraper

[English](README.md) | [简体中文](README.zh.md)


## 📖 Project Overview

This project is a Python based crawler tool for crawling **Valorant** race details from the [VLR.gg](https://www.vlr.gg) website. The crawled data is organized into `.ics` files, which can be imported into a calendar application to keep track of the race schedule.

### 🎯 Features

- **🎮 Match Information Crawling**: including the name of the match, match time, teams and score.
- **📅 Calendar File Generation**: convert crawled data to `.ics` file, support importing Google Calendar, Apple Calendar, etc.
- **⚙️ lightweight design**: only rely on a small number of Python libraries, running efficiently.
- **📱 Cross-platform support**: The generated `.ics` files are compatible with all major calendar apps.

---

## 🚀 Quick Start

### 📋 Environment requirements

- **Python 3.x**
- Supported platforms: Windows / macOS / Linux

### 📦 Dependency libraries

```plaintext
requests
BeautifulSoup4
ics
```

### 🔧 Installation steps

**Clone the project or download the source code**:

   ```bash
   git clone https://github.com/Adamchen566/VCT-matches-to-iCal
   cd vlr-gg-scraper
   ```

## 🛠️ Usage

1. **Get the .ics file**.
    - After the script runs, the generated .ics file will be saved in the current directory.

2. **Manually upload to Google Drive**.
    - Upload the .ics file to Google Drive and get the shared link.

3. **Subscribe to Calendar**.
    - iPhone: Open Settings > Calendar > Accounts > Add Account > Other > Add Subscription Calendar and enter the shared link.
    - Google Calendar: Upload .ics file via Settings > Import Calendar.

## 🚧 Future improvements

### ☁️ Automatic cloud disk upload

- Enables `.ics` files to be automatically uploaded to Google Drive or OneDrive, reducing manual operations.

### ⏰ Timed Updates

- Support crawling and updating race information regularly to ensure real-time synchronization of calendar data.

### 🖥️ Graphical Interface

- Develop graphical interface or desktop application to enhance user experience and facilitate non-technical users.

---

## 📜 License

This project follows the **MIT License**, which you are welcome to freely use, modify, and distribute. See the [LICENSE](LICENSE) file for details.

---

## 💬 Feedback and Contributions

### Submit an Issue

If you find any issues or have suggestions for improvements, feel free to submit an [Issue](https://github.com/Adamchen566/VCT-matches-to-iCal/issues).

### Initiate a Pull Request

If you would like to contribute code or documentation, please follow these steps. 1:

1. Fork the project. 2.
2. Create a new branch (`git checkout -b feature/YourFeatureName`). 3.
3. Commit your changes (`git commit -m 'Add some feature'`). 4.
4. Push to the branch (`git push origin feature/YourFeatureName`).
5. launch [Pull Request](https://github.com/your-repo/vlr-gg-scraper/pulls).

Your contribution will help make this project better!

---

## Thanks for using it! 🎉

---