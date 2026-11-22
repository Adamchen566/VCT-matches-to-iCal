"""Desktop viewer for the calendars in this repository.

Shows the live subscription calendar and every archived event in three
views (table, cards, heatmap) and copies the matching subscription link.
All data comes from the .ics files in the repository; nothing is scraped.

Styling follows the 琥珀夜色 (Amber Night) design system.
"""

from __future__ import annotations

import tkinter.font as tkfont
from tkinter import ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from calendar_library import (
    CalendarEntry,
    MatchRow,
    group_names,
    list_calendars,
    load_matches,
    score_matrix,
)


# --- 琥珀夜色 tokens ---------------------------------------------------------
BG_BASE = "#14130F"
BG_SURFACE = "#1C1A15"
BG_RAISED = "#25221B"
BG_OVERLAY = "#2E2A22"
BORDER_SUBTLE = "#34302A"
BORDER_CONTROL = "#756C5B"
TEXT_PRIMARY = "#F5F0E1"
TEXT_SECONDARY = "#BDB5A3"
TEXT_MUTED = "#958C7B"
PRIMARY = "#F5C542"
PRIMARY_HOVER = "#FFD666"
PRIMARY_SUBTLE = "#3A3016"
PRIMARY_BORDER = "#6B5620"
ON_PRIMARY = "#1F1803"
SECONDARY = "#84A9D6"

RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 14

UI_FONTS = ("Noto Sans SC", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC")
MONO_FONTS = ("JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo")

VIEWS = ("表格", "卡片", "热力图")
MAX_CARDS = 200

HEATMAP_COLORS = LinearSegmentedColormap.from_list(
    "amber_night", [BG_RAISED, PRIMARY_BORDER, PRIMARY]
)


def first_available(candidates: tuple[str, ...], fallback: str) -> str:
    installed = set(tkfont.families())
    return next((name for name in candidates if name in installed), fallback)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=BG_BASE)
        self.title("VCT 日历")
        self.geometry("1200x800")
        self.minsize(960, 600)

        self.ui_font = first_available(UI_FONTS, "TkDefaultFont")
        self.mono_font = first_available(MONO_FONTS, "TkFixedFont")

        self.entries = list_calendars()
        self.groups = group_names(self.entries)
        self.current_group: str | None = None
        self.current_entry: CalendarEntry | None = None
        self.matches: list[MatchRow] = []
        self.view = VIEWS[0]
        self.calendar_buttons: dict[CalendarEntry, ctk.CTkButton] = {}

        self._style_table()
        self._build_layout()

        if self.groups:
            self.select_group(self.groups[0])
        else:
            self._show_message("没有找到日历文件")

    # --- layout ---------------------------------------------------------------
    def _font(self, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(family=self.ui_font, size=size, weight=weight)

    def _segmented(self, parent, values, command) -> ctk.CTkSegmentedButton:
        return ctk.CTkSegmentedButton(
            parent,
            values=list(values),
            command=command,
            font=self._font(13),
            corner_radius=RADIUS_MD,
            fg_color=BG_SURFACE,
            selected_color=BG_OVERLAY,
            selected_hover_color=BG_OVERLAY,
            unselected_color=BG_SURFACE,
            unselected_hover_color=BG_RAISED,
            text_color=TEXT_PRIMARY,
        )

    def _build_layout(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            top, text="VCT 日历", font=self._font(20, "bold"), text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.view_selector = self._segmented(top, VIEWS, self.set_view)
        self.view_selector.set(self.view)
        self.view_selector.pack(side="right")

        self.group_selector = self._segmented(top, self.groups, self.select_group)
        self.group_selector.pack(side="right", padx=16)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=12)
        ctk.CTkLabel(
            bottom, text="订阅链接", font=self._font(12), text_color=TEXT_SECONDARY
        ).pack(side="left")
        self.link_var = ctk.StringVar(value="")
        ctk.CTkEntry(
            bottom,
            textvariable=self.link_var,
            state="readonly",
            font=ctk.CTkFont(family=self.mono_font, size=12),
            fg_color=BG_BASE,
            border_color=BORDER_CONTROL,
            border_width=1,
            corner_radius=RADIUS_MD,
            text_color=TEXT_PRIMARY,
        ).pack(side="left", fill="x", expand=True, padx=12)
        # The one amber primary action on this screen.
        self.copy_button = ctk.CTkButton(
            bottom,
            text="复制",
            width=96,
            command=self.copy_link,
            font=self._font(13, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color=ON_PRIMARY,
            corner_radius=RADIUS_MD,
        )
        self.copy_button.pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16)

        self.sidebar = ctk.CTkScrollableFrame(
            body,
            width=260,
            fg_color=BG_SURFACE,
            border_width=1,
            border_color=BORDER_SUBTLE,
            corner_radius=RADIUS_MD,
            scrollbar_button_color=BG_OVERLAY,
            scrollbar_button_hover_color=BORDER_CONTROL,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))

        main = ctk.CTkFrame(
            body,
            fg_color=BG_SURFACE,
            border_width=1,
            border_color=BORDER_SUBTLE,
            corner_radius=RADIUS_MD,
        )
        main.pack(side="left", fill="both", expand=True)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))
        self.heading = ctk.CTkLabel(
            header, text="", font=self._font(16, "bold"), text_color=TEXT_PRIMARY
        )
        self.heading.pack(side="left")
        self.summary = ctk.CTkLabel(
            header, text="", font=self._font(12), text_color=TEXT_MUTED
        )
        self.summary.pack(side="left", padx=12)

        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _style_table(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        # Drop the theme's outer border; the card around the table has its own.
        style.layout("Amber.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure(
            "Amber.Treeview",
            background=BG_SURFACE,
            fieldbackground=BG_SURFACE,
            foreground=TEXT_PRIMARY,
            bordercolor=BG_SURFACE,
            lightcolor=BG_SURFACE,
            darkcolor=BG_SURFACE,
            borderwidth=0,
            rowheight=30,
            font=(self.ui_font, 11),
        )
        style.configure(
            "Amber.Treeview.Heading",
            background=BG_RAISED,
            foreground=TEXT_SECONDARY,
            bordercolor=BG_RAISED,
            lightcolor=BG_RAISED,
            darkcolor=BG_RAISED,
            relief="flat",
            font=(self.ui_font, 11, "bold"),
        )
        style.map(
            "Amber.Treeview",
            background=[("selected", PRIMARY_SUBTLE)],
            foreground=[("selected", TEXT_PRIMARY)],
        )
        style.map("Amber.Treeview.Heading", background=[("active", BG_OVERLAY)])

    # --- selection --------------------------------------------------------------
    def select_group(self, group: str) -> None:
        self.current_group = group
        self.group_selector.set(group)
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        self.calendar_buttons = {}

        in_group = [entry for entry in self.entries if entry.group == group]
        for entry in in_group:
            button = ctk.CTkButton(
                self.sidebar,
                text=entry.title,
                anchor="w",
                height=34,
                font=self._font(13),
                fg_color="transparent",
                hover_color=BG_OVERLAY,
                text_color=TEXT_PRIMARY,
                border_width=1,
                border_color=BG_SURFACE,
                corner_radius=RADIUS_MD,
                command=lambda selected=entry: self.select_calendar(selected),
            )
            button.pack(fill="x", padx=4, pady=2)
            self.calendar_buttons[entry] = button

        if in_group:
            self.select_calendar(in_group[0])

    def select_calendar(self, entry: CalendarEntry) -> None:
        self.current_entry = entry
        for other, button in self.calendar_buttons.items():
            selected = other == entry
            button.configure(
                fg_color=PRIMARY_SUBTLE if selected else "transparent",
                border_color=PRIMARY_BORDER if selected else BG_SURFACE,
            )

        try:
            self.matches = load_matches(entry.path)
        except (OSError, ValueError) as exc:
            self.matches = []
            self.heading.configure(text=entry.title)
            self.summary.configure(text="")
            self._show_message(f"无法读取 {entry.path.name}：{exc}")
            return

        played = sum(1 for match in self.matches if match.score1 is not None)
        self.heading.configure(text=entry.title)
        self.summary.configure(
            text=f"共 {len(self.matches)} 场 · 已有比分 {played} 场 · 时间为本机时区"
        )
        self.link_var.set(entry.subscribe_url)
        self.copy_button.configure(text="复制")
        self.render()

    def set_view(self, view: str) -> None:
        self.view = view
        self.view_selector.set(view)
        self.render()

    def copy_link(self) -> None:
        if not self.link_var.get():
            return
        self.clipboard_clear()
        self.clipboard_append(self.link_var.get())
        self.copy_button.configure(text="已复制")

    # --- views ------------------------------------------------------------------
    def _clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

    def _show_message(self, text: str) -> None:
        self._clear_content()
        ctk.CTkLabel(
            self.content, text=text, font=self._font(13), text_color=TEXT_MUTED
        ).pack(expand=True)

    def render(self) -> None:
        self._clear_content()
        if not self.matches:
            self._show_message("VLR 尚未公布赛程，公布后会自动出现在这里")
        elif self.view == "表格":
            self._render_table()
        elif self.view == "卡片":
            self._render_cards()
        else:
            self._render_heatmap()

    def _render_table(self) -> None:
        columns = ("时间", "赛区", "队伍 1", "队伍 2", "比分")
        tree = ttk.Treeview(
            self.content, columns=columns, show="headings", style="Amber.Treeview"
        )
        widths = {"时间": 150, "赛区": 90, "队伍 1": 220, "队伍 2": 220, "比分": 70}
        for column in columns:
            tree.heading(column, text=column)
            tree.column(
                column,
                width=widths[column],
                anchor="w" if column.startswith("队伍") else "center",
            )
        for match in self.matches:
            tree.insert(
                "",
                "end",
                values=(
                    match.local_time_text(),
                    match.region,
                    match.team1,
                    match.team2,
                    match.score,
                ),
            )

        scrollbar = ctk.CTkScrollbar(
            self.content,
            command=tree.yview,
            fg_color=BG_SURFACE,
            button_color=BG_OVERLAY,
            button_hover_color=BORDER_CONTROL,
        )
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", pady=4)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)

    def _render_cards(self) -> None:
        scroll = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent",
            scrollbar_button_color=BG_OVERLAY,
            scrollbar_button_hover_color=BORDER_CONTROL,
        )
        scroll.pack(fill="both", expand=True)

        for match in self.matches[:MAX_CARDS]:
            card = ctk.CTkFrame(
                scroll,
                fg_color=BG_RAISED,
                border_width=1,
                border_color=BORDER_SUBTLE,
                corner_radius=RADIUS_MD,
            )
            card.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(
                card,
                text=f"{match.local_time_text()}   {match.region}",
                font=ctk.CTkFont(family=self.mono_font, size=11),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=12, pady=(8, 0))

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(2, 8))
            ctk.CTkLabel(
                row,
                text=f"{match.team1}  vs  {match.team2}",
                font=self._font(14, "bold"),
                text_color=TEXT_PRIMARY,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=match.score,
                font=ctk.CTkFont(family=self.mono_font, size=14, weight="bold"),
                text_color=SECONDARY,
            ).pack(side="right")

        if len(self.matches) > MAX_CARDS:
            ctk.CTkLabel(
                scroll,
                text=f"卡片视图只显示前 {MAX_CARDS} 场，完整列表请切换到表格视图",
                font=self._font(12),
                text_color=TEXT_MUTED,
            ).pack(pady=12)

    def _render_heatmap(self) -> None:
        teams, matrix = score_matrix(self.matches)
        if not teams:
            self._show_message("还没有比分，无法绘制热力图")
            return

        figure = Figure(figsize=(6, 4), facecolor=BG_SURFACE, layout="constrained")
        axes = figure.add_subplot(111)
        axes.set_facecolor(BG_SURFACE)
        peak = max(max(row) for row in matrix) or 1
        axes.imshow(matrix, cmap=HEATMAP_COLORS, vmin=0, vmax=peak)

        label_size = 9 if len(teams) <= 16 else 6
        axes.set_xticks(range(len(teams)), labels=teams, rotation=45, ha="right")
        axes.set_yticks(range(len(teams)), labels=teams)
        axes.tick_params(colors=TEXT_SECONDARY, labelsize=label_size, length=0)
        for spine in axes.spines.values():
            spine.set_visible(False)
        axes.set_xlabel("对手", color=TEXT_MUTED, fontsize=10)
        axes.set_ylabel("队伍（格内为对该对手赢下的地图数）", color=TEXT_MUTED, fontsize=10)

        if len(teams) <= 24:
            for row_index, row in enumerate(matrix):
                for column_index, value in enumerate(row):
                    if value == 0:
                        continue
                    axes.text(
                        column_index,
                        row_index,
                        str(value),
                        ha="center",
                        va="center",
                        fontsize=label_size,
                        color=ON_PRIMARY if value > peak * 0.6 else TEXT_PRIMARY,
                    )

        canvas = FigureCanvasTkAgg(figure, master=self.content)
        canvas.draw()
        canvas.get_tk_widget().configure(background=BG_SURFACE, highlightthickness=0)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)


def run_gui() -> None:
    import matplotlib

    # Team names are Latin, axis labels are Chinese: prefer a CJK-capable font.
    matplotlib.rcParams["font.sans-serif"] = [*UI_FONTS, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    ctk.set_appearance_mode("dark")
    App().mainloop()


if __name__ == "__main__":
    run_gui()
