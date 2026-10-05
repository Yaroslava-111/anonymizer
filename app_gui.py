import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd

from anonymizer import anonymize_dataframe
from column_detector import detect_personal_columns
from deanonymizer import deanonymize_dataframe
from mapping_store import load_mapping, save_mapping

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#e94560"
ACCENT_HOVER = "#ff6b81"
SUCCESS = "#2ecc71"
TYPE_COLORS = {
    "name": "#3498db",
    "phone": "#e67e22",
    "email": "#9b59b6",
    "passport": "#1abc9c",
    "inn": "#e74c3c",
    "address": "#f39c12",
    "birth_date": "#2ecc71",
}


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, original_df, processed_df=None, title="Предпросмотр данных"):
        super().__init__(parent)
        self.title(title)
        self.geometry("1200x600")
        self.minsize(800, 400)

        self.original_df = original_df
        self.processed_df = processed_df

        self._build_ui()
        self._fill_tables()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill=tk.X, padx=15, pady=10)
        ctk.CTkLabel(header, text="\u2731  Предпросмотр", font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT).pack(side=tk.LEFT)
        info = f"{len(self.original_df)} строк \u2022 {len(self.original_df.columns)} колонок"
        ctk.CTkLabel(header, text=info, font=("Segoe UI", 13),
                     text_color="gray60").pack(side=tk.RIGHT)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        left_frame = ctk.CTkFrame(container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 7))

        right_frame = ctk.CTkFrame(container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 0))

        self.left_label = ctk.CTkLabel(left_frame, text="\u25c9  Исходные данные",
                                       font=("Segoe UI", 14, "bold"), anchor=tk.W)
        self.left_label.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.right_label = ctk.CTkLabel(right_frame, text="\u25c9  Обработанные данные",
                                        font=("Segoe UI", 14, "bold"), anchor=tk.W)
        self.right_label.pack(fill=tk.X, padx=10, pady=(10, 5))

        style = self._make_style()

        left_tree_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        left_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.left_scroll_y = ctk.CTkScrollbar(left_tree_frame, orientation="vertical")
        self.left_scroll_x = ctk.CTkScrollbar(left_tree_frame, orientation="horizontal")
        self.left_tree = tk.ttk.Treeview(left_tree_frame, style="Preview.Treeview",
                                         yscrollcommand=self.left_scroll_y.set,
                                         xscrollcommand=self.left_scroll_x.set)
        self.left_scroll_y.configure(command=self.left_tree.yview)
        self.left_scroll_x.configure(command=self.left_tree.xview)

        self.left_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.left_tree.pack(fill=tk.BOTH, expand=True)

        right_tree_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        right_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.right_scroll_y = ctk.CTkScrollbar(right_tree_frame, orientation="vertical")
        self.right_scroll_x = ctk.CTkScrollbar(right_tree_frame, orientation="horizontal")
        self.right_tree = tk.ttk.Treeview(right_tree_frame, style="Preview.Treeview",
                                          yscrollcommand=self.right_scroll_y.set,
                                          xscrollcommand=self.right_scroll_x.set)
        self.right_scroll_y.configure(command=self.right_tree.yview)
        self.right_scroll_x.configure(command=self.right_tree.xview)

        self.right_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.right_tree.pack(fill=tk.BOTH, expand=True)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.status_var = tk.StringVar()
        ctk.CTkLabel(bottom, textvariable=self.status_var, font=("Segoe UI", 12),
                     text_color="gray60").pack(side=tk.RIGHT)

    def _make_style(self):
        import tkinter.ttk as ttk
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Preview.Treeview",
                        background="#1a1a2e",
                        foreground="#eaeaea",
                        fieldbackground="#1a1a2e",
                        font=("Consolas", 11),
                        rowheight=30,
                        borderwidth=0)
        style.configure("Preview.Treeview.Heading",
                        background="#16213e",
                        foreground=ACCENT,
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=1,
                        relief="flat")
        style.map("Preview.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#fff")])
        style.map("Preview.Treeview.Heading",
                  background=[("active", "#1a1a2e")])
        return style

    def _fill_tables(self):
        self._fill_tree(self.left_tree, self.original_df)
        if self.processed_df is not None:
            self._fill_tree(self.right_tree, self.processed_df)
            right_info = f"{len(self.processed_df)} строк \u2022 {len(self.processed_df.columns)} колонок"
            self.right_label.configure(text=f"\u25c9  Обработанные данные  ({right_info})")
        else:
            self.right_label.configure(text="\u25c9  Обработанные данные  (нет данных)")
        left_info = f"{len(self.original_df)} строк \u2022 {len(self.original_df.columns)} колонок"
        self.left_label.configure(text=f"\u25c9  Исходные данные  ({left_info})")
        self.status_var.set(f"Показано {len(self.original_df)} строк \u2022 {len(self.original_df.columns)} колонок")

    def _fill_tree(self, tree, df):
        tree.delete(*tree.get_children())
        cols = [f"col{i}" for i in range(len(df.columns))]
        tree["columns"] = cols
        tree["show"] = "headings"

        for i, col_name in enumerate(df.columns):
            tree.heading(cols[i], text=str(col_name))
            max_w = max(len(str(col_name)) * 9, 80)
            for val in df[col_name].head(50):
                max_w = max(max_w, len(str(val)) * 8 + 20)
            tree.column(cols[i], width=min(max_w, 250), minwidth=60)

        for _, row in df.head(200).iterrows():
            vals = [str(v)[:80] for v in row.values]
            tree.insert("", tk.END, values=vals)


class AnonymizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Анонимизатор — Безопасная анонимизация данных")
        self.geometry("980x720")
        self.minsize(980, 720)

        self.input_path = tk.StringVar()
        self.mapping_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.mode = tk.StringVar(value="anonymize")
        self.detected_columns = []
        self.check_vars = {}
        self._last_original_df = None
        self._last_processed_df = None
        self._last_preview_title = "Предпросмотр данных"
        self._checkbox_frames = []

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=25, pady=20)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(header, text="\u2731  Анонимизатор", font=("Segoe UI", 20, "bold"),
                     text_color=ACCENT).pack(anchor=tk.W)
        ctk.CTkLabel(header, text="Безопасная анонимизация табличных данных  \u2022  Полностью оффлайн",
                     font=("Segoe UI", 13), text_color="gray60").pack(anchor=tk.W, pady=(2, 0))

        mode_card = ctk.CTkFrame(main)
        mode_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        mode_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mode_card, text="Режим работы", font=("Segoe UI", 14, "bold"),
                     anchor=tk.W).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        modes = ctk.CTkFrame(mode_card, fg_color="transparent")
        modes.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 12))

        self._mode_btn_anon = ctk.CTkButton(
            modes, text="\u25c9  Анонимизация", width=200, height=38,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=("Segoe UI", 14, "bold"),
            command=lambda: self._set_mode("anonymize"))
        self._mode_btn_anon.pack(side=tk.LEFT, padx=(0, 8))

        self._mode_btn_deanon = ctk.CTkButton(
            modes, text="\u25cb  Восстановление", width=200, height=38,
            fg_color="gray25", hover_color="gray35",
            font=("Segoe UI", 14),
            command=lambda: self._set_mode("deanonymize"))
        self._mode_btn_deanon.pack(side=tk.LEFT)

        file_card = ctk.CTkFrame(main)
        file_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        file_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(file_card, text="Файлы", font=("Segoe UI", 14, "bold"),
                     anchor=tk.W).grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(12, 8))

        ctk.CTkLabel(file_card, text="Входной файл:", font=("Segoe UI", 13),
                     text_color="gray60", anchor=tk.W).grid(row=1, column=0, sticky="w", padx=(15, 8), pady=4)
        ctk.CTkEntry(file_card, textvariable=self.input_path, font=("Consolas", 13),
                     placeholder_text="Выберите файл...").grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ctk.CTkButton(file_card, text="Обзор", width=90, height=32,
                      fg_color="gray25", hover_color="gray35",
                      font=("Segoe UI", 13),
                      command=self._browse_input).grid(row=1, column=2, padx=(0, 15), pady=4)

        self._lbl_mapping = ctk.CTkLabel(file_card, text="Файл маппинга:", font=("Segoe UI", 13),
                                         text_color="gray60", anchor=tk.W)
        self._lbl_mapping.grid(row=2, column=0, sticky="w", padx=(15, 8), pady=4)
        ctk.CTkEntry(file_card, textvariable=self.mapping_path, font=("Consolas", 13),
                     placeholder_text="Для восстановления...").grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ctk.CTkButton(file_card, text="Обзор", width=90, height=32,
                      fg_color="gray25", hover_color="gray35",
                      font=("Segoe UI", 13),
                      command=self._browse_mapping).grid(row=2, column=2, padx=(0, 15), pady=4)

        ctk.CTkLabel(file_card, text="Выходной файл:", font=("Segoe UI", 13),
                     text_color="gray60", anchor=tk.W).grid(row=3, column=0, sticky="w", padx=(15, 8), pady=(4, 12))
        ctk.CTkEntry(file_card, textvariable=self.output_path, font=("Consolas", 13),
                     placeholder_text="Авто, если пусто...").grid(row=3, column=1, sticky="ew", padx=8, pady=(4, 12))
        ctk.CTkButton(file_card, text="Обзор", width=90, height=32,
                      fg_color="gray25", hover_color="gray35",
                      font=("Segoe UI", 13),
                      command=self._browse_output).grid(row=3, column=2, padx=(0, 15), pady=(4, 12))

        col_card = ctk.CTkFrame(main)
        col_card.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        col_card.grid_columnconfigure(0, weight=1)
        col_card.grid_rowconfigure(1, weight=1)
        main.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(col_card, text="Колонки для обработки", font=("Segoe UI", 14, "bold"),
                     anchor=tk.W).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 0))

        self.col_frame = ctk.CTkScrollableFrame(col_card, fg_color="transparent")
        self.col_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 12))
        self._show_placeholder()

        bottom = ctk.CTkFrame(main, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", pady=(5, 0))
        bottom.grid_columnconfigure(0, weight=1)

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="ew")

        self.run_btn = ctk.CTkButton(
            btn_row, text="\u25b6  Выполнить", width=190, height=42,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            font=("Segoe UI", 13, "bold"),
            command=self._run)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.detect_btn = ctk.CTkButton(
            btn_row, text="\u21bb  Определить колонки", width=220, height=42,
            fg_color="#2563a0", hover_color="#1e5085",
            font=("Segoe UI", 13),
            command=self._detect_columns)
        self.detect_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.preview_btn = ctk.CTkButton(
            btn_row, text="\u25a1  Просмотр", width=150, height=42,
            fg_color="#2563a0", hover_color="#1e5085",
            font=("Segoe UI", 13),
            command=self._open_preview)
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = ctk.CTkButton(
            btn_row, text="\u2716  Очистить", width=150, height=42,
            fg_color="#6b7280", hover_color="#4b5563",
            font=("Segoe UI", 13),
            command=self._clear_all)
        self.clear_btn.pack(side=tk.LEFT)

        status_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        status_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.status_var = tk.StringVar(value="\u2713  Готово к работе")
        ctk.CTkLabel(status_frame, textvariable=self.status_var, font=("Segoe UI", 12),
                     text_color="gray60").pack(anchor=tk.W)

        self.progress = ctk.CTkProgressBar(bottom, height=4, fg_color="gray25",
                                           progress_color=ACCENT)
        self.progress.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.progress.set(0)

    def _show_placeholder(self):
        for w in self.col_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.col_frame, text="Выберите входной файл — колонки определятся автоматически",
                     font=("Segoe UI", 13), text_color="gray60").pack(anchor=tk.W, pady=8, padx=10)

    def _set_mode(self, mode):
        self.mode.set(mode)
        if mode == "deanonymize":
            self._mode_btn_anon.configure(fg_color="gray25", font=("Segoe UI", 14))
            self._mode_btn_deanon.configure(fg_color=ACCENT, font=("Segoe UI", 14, "bold"))
            self._lbl_mapping.configure(text="Файл маппинга: \u26a0")
        else:
            self._mode_btn_anon.configure(fg_color=ACCENT, font=("Segoe UI", 14, "bold"))
            self._mode_btn_deanon.configure(fg_color="gray25", font=("Segoe UI", 14))
            self._lbl_mapping.configure(text="Файл маппинга:")
        if self.input_path.get() and os.path.exists(self.input_path.get()):
            self._detect_columns()

    def _browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")])
        if path:
            self.input_path.set(path)
            if self.mode.get() == "deanonymize":
                self._auto_find_mapping(path)
            self._detect_columns()

    def _auto_find_mapping(self, input_path):
        base = os.path.splitext(input_path)[0]
        for suffix in ["_mapping.json", "_anonymous_mapping.json"]:
            candidate = base + suffix
            if os.path.exists(candidate):
                self.mapping_path.set(candidate)
                return
        for f in os.listdir(os.path.dirname(input_path) or "."):
            if f.endswith("_mapping.json") and os.path.splitext(os.path.basename(input_path))[0] in f:
                full = os.path.join(os.path.dirname(input_path) or ".", f)
                self.mapping_path.set(full)
                return

    def _browse_mapping(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("Зашифрованный", "*.enc")])
        if path:
            self.mapping_path.set(path)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if path:
            self.output_path.set(path)

    def _load_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return pd.read_csv(path, encoding="utf-8")
        return pd.read_excel(path, engine="openpyxl")

    def _save_file(self, df, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df.to_csv(path, index=False, encoding="utf-8")
        else:
            df.to_excel(path, index=False, engine="openpyxl")

    def _detect_columns(self):
        path = self.input_path.get()
        if not path or not os.path.exists(path):
            return
        try:
            df = self._load_file(path)
            if self.mode.get() == "deanonymize":
                self._show_preview_inplace(df)
            else:
                self.detected_columns = detect_personal_columns(df)
                self._rebuild_column_checks()
            self.status_var.set(f"\u2713  {len(df)} строк  \u2022  {len(df.columns)} колонок")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")

    def _show_preview_inplace(self, df):
        for w in self.col_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.col_frame, text="Превью данных (первые 5 строк):",
                     font=("Segoe UI", 13), text_color="gray60").pack(anchor=tk.W, pady=(0, 4), padx=10)
        for i, row in df.head(5).iterrows():
            vals = " | ".join(str(v)[:20] for v in row.values[:6])
            ctk.CTkLabel(self.col_frame, text=f"  {vals}",
                         font=("Consolas", 11), text_color="#eaeaea", anchor=tk.W).pack(anchor=tk.W, padx=10)
        if self.mapping_path.get() and os.path.exists(self.mapping_path.get()):
            m = load_mapping(self.mapping_path.get())
            info_parts = []
            for cn, cd in m.get("columns", {}).items():
                info_parts.append(f"{cn} ({len(cd.get('mapping', {}))} значений)")
            ctk.CTkLabel(self.col_frame, text=f"\nМаппинг: {', '.join(info_parts)}",
                         font=("Segoe UI", 12), text_color=SUCCESS).pack(anchor=tk.W, pady=(8, 0), padx=10)

    def _rebuild_column_checks(self):
        for w in self.col_frame.winfo_children():
            w.destroy()
        self.check_vars.clear()
        self._checkbox_frames.clear()

        if not self.detected_columns:
            ctk.CTkLabel(self.col_frame, text="Персональные колонки не обнаружены",
                         font=("Segoe UI", 13), text_color="gray60").pack(anchor=tk.W, pady=8, padx=10)
            return

        for col_name, col_type in self.detected_columns:
            var = tk.BooleanVar(value=True)
            self.check_vars[col_name] = var
            tc = TYPE_COLORS.get(col_type, "gray60")

            row = ctk.CTkFrame(self.col_frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=2, padx=5)

            cb = ctk.CTkCheckBox(
                row, text="", variable=var, width=22,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                checkmark_color="#fff")
            cb.pack(side=tk.LEFT, padx=(0, 8))

            ctk.CTkLabel(row, text=col_name, font=("Segoe UI", 13),
                         text_color="#eaeaea").pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=f"  {col_type}", font=("Segoe UI", 12),
                         text_color=tc).pack(side=tk.LEFT)
            self._checkbox_frames.append(row)

    def _run(self):
        if not self.input_path.get():
            messagebox.showwarning("Внимание", "Укажите входной файл.")
            return
        self.run_btn.configure(state="disabled")
        self.detect_btn.configure(state="disabled")
        self.preview_btn.configure(state="disabled")
        self.status_var.set("\u23f3  Обработка...")
        self.progress.set(0.3)
        threading.Thread(target=self._run_task, daemon=True).start()

    def _run_task(self):
        try:
            if self.mode.get() == "anonymize":
                self._do_anonymize()
            else:
                self._do_deanonymize()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.after(0, self._done)

    def _do_anonymize(self):
        df = self._load_file(self.input_path.get())
        columns = [c for c, v in self.check_vars.items() if v.get()]
        if not columns:
            self.after(0, lambda: messagebox.showwarning("Внимание", "Выберите хотя бы одну колонку."))
            return

        existing = None
        mp = self.mapping_path.get()
        if mp and os.path.exists(mp):
            existing = load_mapping(mp)

        self.after(0, lambda: self.progress.set(0.6))
        anon_df, mapping, stats = anonymize_dataframe(df, columns, existing)
        self._last_original_df = df
        self._last_processed_df = anon_df
        self._last_preview_title = "До / После анонимизации"

        output = self.output_path.get()
        if not output:
            base, ext = os.path.splitext(self.input_path.get())
            output = f"{base}_anonymous{ext}"

        self._save_file(anon_df, output)

        mapping_file = mp if mp and mp.endswith(".json") else os.path.splitext(output)[0] + "_mapping.json"
        if self.mapping_path.get() and not self.mapping_path.get().endswith(".json"):
            mapping_file = self.mapping_path.get()
        save_mapping(mapping, mapping_file)

        self.after(0, lambda: self.progress.set(1.0))
        msg = "Анонимизация завершена!\n\n"
        for col, count in stats.items():
            msg += f"  {col}: {count} значений \u2192 индексы\n"
        msg += f"\nФайл: {output}\nМаппинг: {mapping_file}"
        self.after(0, lambda: messagebox.showinfo("Готово", msg))
        self.after(0, lambda: self.status_var.set("\u2713  Анонимизация завершена"))

    def _do_deanonymize(self):
        mp = self.mapping_path.get()
        if not mp or not os.path.exists(mp):
            self.after(0, lambda: messagebox.showwarning("Внимание", "Укажите файл маппинга."))
            return

        df = self._load_file(self.input_path.get())
        mapping = load_mapping(mp)
        self.after(0, lambda: self.progress.set(0.6))
        restored_df, stats = deanonymize_dataframe(df, mapping)
        self._last_original_df = df
        self._last_processed_df = restored_df
        self._last_preview_title = "До / После восстановления"

        output = self.output_path.get()
        if not output:
            base, ext = os.path.splitext(self.input_path.get())
            output = f"{base}_restored{ext}"

        self._save_file(restored_df, output)

        self.after(0, lambda: self.progress.set(1.0))
        msg = "Восстановление завершено!\n\n"
        for col_name, s in stats.items():
            msg += f"  {col_name}: {s['total']} строк, не найдено: {s['unmapped']}\n"
        msg += f"\nФайл: {output}"
        self.after(0, lambda: messagebox.showinfo("Готово", msg))
        self.after(0, lambda: self.status_var.set("\u2713  Восстановление завершена"))

    def _done(self):
        self.run_btn.configure(state="normal")
        self.detect_btn.configure(state="normal")
        self.preview_btn.configure(state="normal")
        self.progress.set(0)

    def _open_preview(self):
        path = self.input_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Внимание", "Сначала загрузите входной файл.")
            return
        try:
            original_df = self._load_file(path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")
            return

        processed_df = self._last_processed_df
        title = self._last_preview_title
        if processed_df is None:
            processed_df = original_df
            title = "Данные (пока не обработаны — показаны исходные)"

        PreviewWindow(self, original_df, processed_df, title)

    def _clear_all(self):
        self.input_path.set("")
        self.mapping_path.set("")
        self.output_path.set("")
        self.detected_columns = []
        self.check_vars.clear()
        self._last_original_df = None
        self._last_processed_df = None
        self._last_preview_title = "Предпросмотр данных"
        self._show_placeholder()
        self.status_var.set("\u2713  Готово к работе")
        self.progress.set(0)


def main():
    app = AnonymizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
