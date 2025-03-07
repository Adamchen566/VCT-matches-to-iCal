# VLR.gg Valorant Match Scraper

[English](README.md) | [简体中文](README.zh.md)


## Project Overview

### This project comprises a Python-based web scraping tool engineered to systematically extract competitive match data from the VLR.gg platform. The collected data includes:



- Tournament designation

- Scheduled match date and time

- Competing teams

- Match results

#### The retrieved dataset is structured as a list, processed for coherence, and subsequently converted into an iCalendar (.ics) file to facilitate seamless integration with digital calendar systems

### In its current iteration, the iCal file must be manually uploaded to Google Drive to generate a shareable subscription link for iPhone calendar integration. The automation of cloud-based file uploads remains an outstanding enhancement

##### System Requirements:

```
Python 3.x
```

##### Required Libraries:

```
requests

BeautifulSoup4

ics
```


### Installation Procedure

##### Clone the repository or download the source code:


```
git clone https://github.com/your-repo/vlr-gg-scraper.git
cd vlr-gg-scraper
```


##### Install necessary dependencies:


```
pip install -r requirements.txt
```


### Usage Guidelines

##### Execute the web scraper:

```
python scraper.py
```


##### The resulting .ics file will be stored in the local directory.

##### Manually upload the .ics file to Google Drive and retrieve the corresponding shareable link.


##### To subscribe to the calendar on an iPhone:

> Navigate to Settings > Calendar > Accounts > Add Account > Other > Add Subscribed Calendar. Input the shareable link to complete the subscription process.

## Prospective Enhancements

- Implement automated cloud-based file uploads

- Develop scheduled update functionalities based on predefined criteria

- Introduce a graphical user interface for enhanced usability


## Licensing

This project is distributed under the MIT License, permitting unrestricted usage and modifications.

For inquiries, feature requests, or contributions, please submit an issue or pull request via the repository.