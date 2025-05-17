import customtkinter as ctk
from tkinter import ttk
from scrape import get_match_info, sort_key, create_ics_file
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import os

# 初始化样式
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

from links import *

GITHUB_BASE_ICS_URL = "https://adamchen566.github.io/VCT-matches-to-iCal/Calendar_Files/"

# 主 GUI 应用
def run_gui():
    def load_event_buttons(year):
        for widget in right_frame.winfo_children():
            widget.destroy()

        year_events = events_by_year.get(year, {})
        ctk.CTkLabel(right_frame, text=f"{year} 年赛事", font=("Microsoft YaHei", 16, "bold"), pady=10).pack()

        scroll_frame = ctk.CTkScrollableFrame(right_frame, width=330, height=600)
        scroll_frame.pack(fill="both", expand=True)

        last_category = ""
        for event_name, regions in year_events.items():
            category = event_name.split()[0]
            if category != last_category and last_category != "":
                ctk.CTkLabel(scroll_frame, text="").pack(pady=8)

            for region in regions.keys():
                label = f"{event_name} ({region})"
                ctk.CTkButton(scroll_frame, text=label, width=300, height=35,
                              command=lambda y=year, e=event_name, r=region: load_match_views(y, e, r)).pack(pady=4)
            last_category = category

    def load_match_views(year, event_name, region):
        global match_data, current_event_info, selected_year
        selected_year = year  # 记录当前年份
        global match_data, current_event_info
        for widget in info_frame.winfo_children():
            widget.destroy()

        try:
            url = events_by_year[year][event_name][region]
            match_data = []
            get_match_info(url, match_data, region, 0)
            if not match_data:
                return
            match_data.sort(key=sort_key)
            render_views()
            current_event_info = (event_name, region, match_data, url)
            copy_button.configure(text="Copy")
        except Exception as e:
            print("错误:", e)

    def generate_and_copy_ics():
        if not current_event_info:
            return
        event_name, region, matches, link = current_event_info

        filename = f"{selected_year}_{event_name.replace(' ', '_')}_{region}.ics"
        folder = os.path.join(os.path.dirname(__file__), "Calendar_Files")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)

        create_ics_file(link=link, matches=matches, name=event_name)

        web_link = f"{GITHUB_BASE_ICS_URL}{filename}"
        ics_var.set(web_link)
        app.clipboard_clear()
        app.clipboard_append(web_link)
        copy_button.configure(text="Copied")


    def render_views():
        for widget in info_frame.winfo_children():
            widget.destroy()

        if view_mode.get() == "表格":
            table_frame = ctk.CTkFrame(info_frame)
            table_frame.pack(fill="both", expand=True, padx=10, pady=10)

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Treeview",
                            background="#1a1a1a",
                            foreground="white",
                            rowheight=28,
                            fieldbackground="#1a1a1a",
                            font=("Microsoft YaHei", 12))
            style.configure("Treeview.Heading",
                            background="#333333",
                            foreground="white",
                            font=("Microsoft YaHei", 13, "bold"))

            columns = ("时间", "区域", "队伍1", "队伍2", "比分")
            tree = ttk.Treeview(table_frame, columns=columns, show="headings")
            for col in columns:
                tree.heading(col, text=col)
            tree.column("时间", width=150, anchor="center")
            tree.column("区域", width=80, anchor="center")
            tree.column("队伍1", width=160, anchor="center")
            tree.column("队伍2", width=160, anchor="center")
            tree.column("比分", width=60, anchor="center")

            for match in match_data:
                tree.insert("", "end", values=(match['datetime'], match['region'], match['team1'], match['team2'], match['score']))
            tree.pack(fill="both", expand=True)

        elif view_mode.get() == "卡片":
            scroll = ctk.CTkScrollableFrame(info_frame)
            scroll.pack(fill="both", expand=True, padx=10, pady=10)
            for match in match_data:
                text = (f"🕒 {match['datetime']}  |  🌍 {match['region']}\n"
                        f"⚔️  {match['team1']}  vs  {match['team2']}  🎯 比分: {match['score']}")
                card = ctk.CTkFrame(scroll, corner_radius=8)
                ctk.CTkLabel(card, text=text, justify="left", font=("Microsoft YaHei", 13)).pack(padx=10, pady=10)
                card.pack(fill="x", padx=5, pady=6)

        elif view_mode.get() == "热力图":
            matrix = {}
            teams = set()
            for m in match_data:
                if m['score'] and ":" in m['score']:
                    t1, t2 = m['team1'], m['team2']
                    s1, s2 = map(int, m['score'].split(":"))
                    matrix.setdefault(t1, {}).setdefault(t2, 0)
                    matrix[t1][t2] += s1
                    matrix.setdefault(t2, {}).setdefault(t1, 0)
                    matrix[t2][t1] += s2
                    teams.update([t1, t2])

            df = pd.DataFrame(index=sorted(teams), columns=sorted(teams)).fillna(0)
            for r in matrix:
                for c in matrix[r]:
                    df.loc[r, c] = matrix[r][c]

            fig, ax = plt.subplots(figsize=(10, 8))
            sns.set_theme(style="whitegrid")
            heatmap = sns.heatmap(df.astype(int), annot=True, fmt="d", cmap="YlOrRd",
                                  linewidths=0.5, linecolor='gray', square=True, cbar=True, ax=ax)
            ax.set_title("Team Score Heatmap", fontsize=16, fontweight='bold')
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=10)
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=info_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    app = ctk.CTk()
    app.geometry("1200x800")
    app.title("VCT 日历生成器 (2021–2025)")

    top_frame = ctk.CTkFrame(app)
    top_frame.pack(pady=10)

    ctk.CTkLabel(top_frame, text="选择年份:", font=("Microsoft YaHei", 14)).pack(side="left", padx=10)
    for y in events_by_year.keys():
        ctk.CTkButton(top_frame, text=y, width=60, command=lambda year=y: load_event_buttons(year)).pack(side="left", padx=5)

    global view_mode
    view_mode = ctk.StringVar(value="表格")
    ctk.CTkSegmentedButton(top_frame, values=["表格", "卡片", "热力图"], variable=view_mode, command=lambda _: render_views()).pack(side="left", padx=15)

    main_frame = ctk.CTkFrame(app)
    main_frame.pack(expand=True, fill="both", padx=10, pady=10)

    global right_frame, info_frame, match_data, ics_var, current_event_info, copy_button
    match_data = []
    current_event_info = None
    right_frame = ctk.CTkFrame(main_frame, width=350)
    right_frame.pack(side="left", fill="y", padx=(0, 10))

    info_frame = ctk.CTkFrame(main_frame)
    info_frame.pack(side="left", fill="both", expand=True)

    # Bottom frame for .ics link
    bottom_frame = ctk.CTkFrame(app)
    bottom_frame.pack(fill="x", padx=20, pady=8)
    ics_var = ctk.StringVar(value="")
    ctk.CTkLabel(bottom_frame, text="ICS Subscribe Link:", width=140).pack(side="left")
    ics_entry = ctk.CTkEntry(bottom_frame, textvariable=ics_var, width=800)
    ics_entry.pack(side="left", padx=8)
    copy_button = ctk.CTkButton(bottom_frame, text="Copy", command=generate_and_copy_ics)
    copy_button.pack(side="left")

    app.mainloop()

if __name__ == '__main__':
    run_gui()