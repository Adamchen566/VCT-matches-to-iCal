# VCT Calendar Generator GUI (Button UI + Full Year/Event Support)

import tkinter as tk
from tkinter import messagebox
from scrape import get_match_info, sort_key, create_ics_file

# 所有年份与赛事信息
events_by_year = {
    "2021": {
        "Masters Reykjavik": {"ALL": "https://www.vlr.gg/event/matches/353/valorant-champions-tour-stage-2-masters-reykjav-k/?series_id=all"},
        "Masters Berlin": {"ALL": "https://www.vlr.gg/event/matches/466/valorant-champions-tour-stage-3-masters-berlin/?series_id=all"},
        "Champions 2021": {"ALL": "https://www.vlr.gg/event/matches/449/valorant-champions-2021/?series_id=all"},
    },
    "2022": {
        "Masters Reykjavik": {"ALL": "https://www.vlr.gg/event/matches/926/valorant-champions-tour-stage-1-masters-reykjav-k/?series_id=all"},
        "Masters Copenhagen": {"ALL": "https://www.vlr.gg/event/matches/1014/valorant-champions-tour-stage-2-masters-copenhagen/?series_id=all"},
        "Champions 2022": {"ALL": "https://www.vlr.gg/event/matches/1015/valorant-champions-2022/?series_id=all"},
    },
    "2023": {
        "Masters Tokyo": {"ALL": "https://www.vlr.gg/event/matches/1494/champions-tour-2023-masters-tokyo/?series_id=all"},
        "Champions 2023": {"ALL": "https://www.vlr.gg/event/matches/1657/valorant-champions-2023/?series_id=all"},
        "LOCK//IN Brazil": {"ALL": "https://www.vlr.gg/event/matches/1361/valorant-lock-in-s-o-paulo/?series_id=all"},
    },
    "2024": {
        "Kickoff": {
            "CN": "https://www.vlr.gg/event/matches/1926/champions-tour-2024-china-kickoff/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/1923/champions-tour-2024-americas-kickoff/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/1924/champions-tour-2024-pacific-kickoff/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/1925/champions-tour-2024-emea-kickoff/?series_id=all"
        },
        "Masters Madrid": {
            "ALL": "https://www.vlr.gg/event/matches/1921/champions-tour-2024-masters-madrid/?series_id=all"
        },
        "Stage 1": {
            "CN": "https://www.vlr.gg/event/matches/2006/champions-tour-2024-china-stage-1/?series_id=3841",
            "AMER": "https://www.vlr.gg/event/matches/2004/champions-tour-2024-americas-stage-1/?series_id=3837",
            "PAC": "https://www.vlr.gg/event/matches/2002/champions-tour-2024-pacific-stage-1/?series_id=3833",
            "EMEA": "https://www.vlr.gg/event/matches/1998/champions-tour-2024-emea-stage-1/?series_id=3826"
        },
        "Masters Shanghai": {
            "ALL": "https://www.vlr.gg/event/matches/1999/champions-tour-2024-masters-shanghai/?series_id=all"
        },
        "Stage 2": {
            "CN": "https://www.vlr.gg/event/matches/2096/champions-tour-2024-china-stage-2/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/2095/champions-tour-2024-americas-stage-2/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/2005/champions-tour-2024-pacific-stage-2/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/2094/champions-tour-2024-emea-stage-2/?series_id=all"
        },
        "Champions Seoul": {
            "ALL": "https://www.vlr.gg/event/matches/2097/valorant-champions-2024/?series_id=all"
        }
    },
    "2025": {
        "Kickoff": {
            "CN": "https://www.vlr.gg/event/matches/2275/champions-tour-2025-china-kickoff/?series_id=all",
            "AMER": "https://www.vlr.gg/event/matches/2274/champions-tour-2025-americas-kickoff/?series_id=all",
            "PAC": "https://www.vlr.gg/event/matches/2277/champions-tour-2025-pacific-kickoff/?series_id=all",
            "EMEA": "https://www.vlr.gg/event/matches/2276/champions-tour-2025-emea-kickoff/?series_id=all"
        },
        "Masters Bangkok": {
            "ALL": "https://www.vlr.gg/event/matches/2281/champions-tour-2025-masters-bangkok/?series_id=all"
        },
        "Stage 1": {
            "CN": "https://www.vlr.gg/event/matches/2359/champions-tour-2025-china-stage-1",
            "AMER": "https://www.vlr.gg/event/matches/2347/champions-tour-2025-americas-stage-1",
            "PAC": "https://www.vlr.gg/event/matches/2379/champions-tour-2025-pacific-stage-1",
            "EMEA": "https://www.vlr.gg/event/matches/2380/champions-tour-2025-emea-stage-1"
        },
        "Masters Toronto": {
            "ALL": "https://www.vlr.gg/event/matches/2282/champions-tour-2025-masters-toronto/?series_id=all"
        },
        "Stage 2": {},
        "Champions Paris": {
            "ALL": "https://www.vlr.gg/event/matches/2283/valorant-champions-2025/?series_id=all"
        }
    }
}

# GUI 主程序
def run_gui():
    def load_event_buttons(year):
        for widget in event_frame.winfo_children():
            widget.destroy()

        year_events = events_by_year.get(year, {})
        tk.Label(event_frame, text=f"{year} 年赛事", font=("Helvetica", 12, "bold"), pady=5).pack()
        for event_name, regions in year_events.items():
            for region in regions.keys():
                label = f"{event_name} ({region})"
                tk.Button(event_frame, text=label, width=35, pady=2,
                          command=lambda y=year, e=event_name, r=region: generate_ics(y, e, r)).pack(pady=1)

    def generate_ics(year, event_name, region):
        try:
            url = events_by_year[year][event_name][region]
            data = []
            get_match_info(url, data, region, 0)
            if data:
                sorted_data = sorted(data, key=sort_key)
                safe_name = event_name.replace(' ', '_').replace('/', '')
                filename = f"VCT_{year}_{safe_name}_{region}"
                create_ics_file(url, sorted_data, filename)
                messagebox.showinfo("成功", f"{filename}.ics 文件已生成！")
            else:
                messagebox.showwarning("无数据", f"未找到 {event_name} ({region}) 的比赛信息。")
        except Exception as e:
            messagebox.showerror("错误", f"发生错误: {e}")

    root = tk.Tk()
    root.title("VCT 日历生成器 (2021–2025)")
    root.geometry("600x600")

    top_frame = tk.Frame(root)
    top_frame.pack(pady=10)
    tk.Label(top_frame, text="选择年份:", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=10)

    for y in events_by_year.keys():
        tk.Button(top_frame, text=y, width=6,
                  command=lambda year=y: load_event_buttons(year)).pack(side=tk.LEFT, padx=3)

    global event_frame
    event_frame = tk.Frame(root)
    event_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    root.mainloop()

if __name__ == '__main__':
    run_gui()
