import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PIL import Image, ImageTk 

# =========================================================================
# 1. STRUKTUR DATA (BACKEND - KEKAL 100% SEPERTI ASAL)
# =========================================================================

class Employee:
    """Simpan data profil dan sesi log setiap pekerja"""
    def __init__(self, emp_id, name, department, status="Absent", clock_in="-", clock_out="-", total_hours="0.00"):
        self.id = emp_id.strip().upper()         
        self.name = name.strip()                 
        self.department = department.strip()     
        self.status = status.strip()             
        self.last_clock_in = clock_in.strip()     
        self.last_clock_out = clock_out.strip()   
        self.total_hours = total_hours.strip()   


class AttendanceSystem:
    """Proses logik sistem (baca/tulis fail, kira masa, import/eksport)"""
    def __init__(self, filename="attendance_data.txt"):
        self.filename, self.all_logs = filename, []
        self.load_data()

    def load_data(self):
        """Muat data dari fail teks utama dengan sokongan pelbagai encoding"""
        if not os.path.exists(self.filename):
            if not (pilihan := filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")], title="Pilih Fail Data Kehadiran")): return
            self.filename = pilihan
        
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        success = False
        
        for enc in encodings_to_try:
            try:
                with open(self.filename, "r", encoding=enc) as f: 
                    lines = f.readlines()
                
                self.all_logs = [] 
                for line in lines:
                    if line.strip():
                        parts = [p.strip() for p in line.strip().split("|")]
                        if len(parts) >= 3:
                            clean_parts = parts + ["-"] * (7 - len(parts))
                            if clean_parts[6] == "-": clean_parts[6] = "0.00"
                            self.all_logs.append(Employee(*clean_parts[:7]))
                
                success = True
                if enc != "utf-8":
                    self.rewrite_all_data()
                break 
            except (UnicodeDecodeError, LookupError):
                continue 
                
        if not success:
            messagebox.showerror("Ralat", "Gagal membaca fail: Format karakter (encoding) tidak disokong.")

    def standardize_datetime(self, date_str):
        if not date_str or date_str.strip() in ["-", ""]: return "-"
        date_str = date_str.strip()
        if date_str.startswith('="') and date_str.endswith('"'): date_str = date_str[2:-1].strip()
        date_str = date_str.replace("\t", "").strip()
        
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M"]:
            try: return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError: continue
        return date_str

    def import_old_data_file(self, filepath):
        count = 0
        try:
            existing_records = {(emp.id.upper(), emp.last_clock_in) for emp in self.all_logs if emp.last_clock_in != "-"}
            existing_profiles = {emp.id.upper() for emp in self.all_logs}
            rows = []
            
            if filepath.endswith('.txt'):
                with open(filepath, "r", encoding="utf-8") as f: rows = [line.strip().split("|") for line in f if line.strip()]
            elif filepath.endswith('.csv'):
                with open(filepath, mode='r', encoding='utf-8') as f: 
                    rows = [r for r in csv.reader(f) if r and not r[0].lower().startswith(("id", "id pekerja"))]
            
            for r in rows:
                if len(r) >= 3:
                    emp_id, name, dept = str(r[0]).strip().upper(), str(r[1]).strip(), str(r[2]).strip()
                    status = str(r[3]).strip() if len(r) > 3 and r[3] else "Absent"
                    c_in = self.standardize_datetime(str(r[4]).strip() if len(r) > 4 and r[4] else "-")
                    c_out = self.standardize_datetime(str(r[5]).strip() if len(r) > 5 and r[5] else "-")
                    t_hours = str(r[6]).strip() if len(r) > 6 and r[6] else "0.00"
                    
                    if c_in in ["-", ""]:
                        if emp_id not in existing_profiles:
                            self.all_logs.append(Employee(emp_id, name, dept, "Absent", "-", "-", "0.00"))
                            existing_profiles.add(emp_id); count += 1
                    else:
                        if (emp_id, c_in) not in existing_records:
                            self.all_logs.append(Employee(emp_id, name, dept, status, c_in, c_out, t_hours))
                            existing_records.add((emp_id, c_in)); count += 1
                            
            if count > 0: 
                self.rewrite_all_data() 
                return True, f"Berjaya mengimport {count} rekod baru."
            return False, "Tiada data baru ditemui."
        except Exception as e: return False, f"Gagal import: {e}"

    def delete_specific_log(self, emp_id, clock_in_time):
        orig_len = len(self.all_logs)
        self.all_logs = [e for e in self.all_logs if not (e.id.upper() == emp_id.strip().upper() and e.last_clock_in == clock_in_time)]
        return (self.rewrite_all_data() or (True, "Log berjaya dipadam.")) if len(self.all_logs) < orig_len else (False, "Log tidak ditemui!")

    def get_latest_status(self, emp_id):
        return next((e for e in reversed(self.all_logs) if e.id.upper() == emp_id.strip().upper()), None)

    def clock_in_employee(self, emp_id):
        if not (latest := self.get_latest_status(emp_id)): return False, "ID belum didaftarkan!"
        if latest.status == "Present": return False, "Pekerja sudah Clock In!"
        
        new_log = Employee(emp_id.strip().upper(), latest.name, latest.department, "Present", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-", "0.00")
        self.all_logs.append(new_log)
        try:
            with open(self.filename, "a", encoding="utf-8") as f: f.write(f"{new_log.id}|{new_log.name}|{new_log.department}|{new_log.status}|{new_log.last_clock_in}|{new_log.last_clock_out}|{new_log.total_hours}\n")
            return True, f"Clock In Berjaya! Selamat bekerja, {latest.name}."
        except Exception as e: return False, f"Gagal menulis fail: {e}"

    def clock_out_employee(self, emp_id):
        if not (latest := self.get_latest_status(emp_id)) or latest.status == "Absent" or latest.last_clock_in == "-": return False, "Perlu Clock In dahulu!"
        
        now = datetime.now()
        latest.last_clock_out, latest.status = now.strftime("%Y-%m-%d %H:%M:%S"), "Absent"
        latest.total_hours = f"{(now - datetime.strptime(latest.last_clock_in, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600:.2f}"
        self.rewrite_all_data() 
        return True, f"Clock Out Berjaya! Masa: {latest.total_hours} jam."

    def create_employee(self, emp_id, name, department):
        if self.get_latest_status(emp_id): return False, "ID sudah wujud!"
        new_emp = Employee(emp_id.strip().upper(), name.strip(), department)
        self.all_logs.append(new_emp)
        try:
            with open(self.filename, "a", encoding="utf-8") as f: f.write(f"{new_emp.id}|{new_emp.name}|{new_emp.department}|{new_emp.status}|{new_emp.last_clock_in}|{new_emp.last_clock_out}|{new_emp.total_hours}\n")
            return True, "Pekerja berjaya didaftarkan."
        except Exception as e: return False, f"Gagal mendaftar: {e}"

    def update_employee(self, emp_id, new_name, new_dept):
        found = False
        for e in self.all_logs:
            if e.id.upper() == emp_id.strip().upper(): e.name, e.department, found = new_name, new_dept, True
        if found: self.rewrite_all_data(); return True, "Profil berjaya dikemaskini."
        return False, "ID tidak ditemui!"

    def delete_employee(self, emp_id):
        orig_len = len(self.all_logs)
        self.all_logs = [e for e in self.all_logs if e.id.upper() != emp_id.strip().upper()]
        if len(self.all_logs) < orig_len: self.rewrite_all_data(); return True, "Semua rekod pekerja dipadam."
        return False, "ID tidak ditemui!"

    def rewrite_all_data(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                for e in self.all_logs: f.write(f"{e.id}|{e.name}|{e.department}|{e.status}|{e.last_clock_in}|{e.last_clock_out}|{e.total_hours}\n")
        except Exception as e: messagebox.showerror("Ralat", f"Gagal kemaskini fail: {e}")

    def export_all_data_to_file(self, filepath):
        try:
            if filepath.endswith('.csv'):
                with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID Pekerja", "Nama Penuh", "Jabatan", "Status Sesi", "Masa Clock In", "Masa Clock Out", "Jam Sesi Ini"])
                    for e in self.all_logs:
                        fmt_in = f'="{e.last_clock_in}"' if e.last_clock_in != "-" else "-"
                        fmt_out = f'="{e.last_clock_out}"' if e.last_clock_out != "-" else "-"
                        writer.writerow([e.id, e.name, e.department, e.status, fmt_in, fmt_out, e.total_hours])
            elif filepath.endswith('.txt'):
                with open(filepath, mode='w', encoding='utf-8') as f:
                    for e in self.all_logs: f.write(f"{e.id}|{e.name}|{e.department}|{e.status}|{e.last_clock_in}|{e.last_clock_out}|{e.total_hours}\n")
            return True, f"Berjaya eksport ke {filepath.split('.')[-1].upper()}!"
        except Exception as e: return False, f"Gagal eksport: {e}"


# =========================================================================
# 2. ANTARAMUKA PENGGUNA (FRONTEND GUI - THEME GLOW CYBERPUNK)
# =========================================================================

class AttendanceGUI:
    """Menguruskan paparan tetingkap aplikasi (Tkinter NEON GLOW STYLE)"""
    def __init__(self, root, system):
        self.root, self.system = root, system
        root.title("Sistem Kehadiran Pekerja - Powered by AURA")
        root.configure(bg="#0e1726")
        root.attributes("-fullscreen", True)
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
        
        # Penetapan Palet Warna Neon / Cyberpunk
        self.BG_MAIN = "#0e1726"
        self.BG_PANEL = "#1b2e4b"
        self.FG_TEXT = "#ffffff"
        self.NEON_CYAN = "#00f2fe"
        self.NEON_GREEN = "#00e676"
        self.NEON_RED = "#ff1744"
        self.NEON_BLUE = "#2196f3"
        
        # Konfigurasi Elemen Global TTK Styles
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        # Gaya untuk Notebook (Tabs)
        self.style.configure("TNotebook", background=self.BG_MAIN, borderwidth=0, highlightthickness=0)
        self.style.configure("TNotebook.Tab", background=self.BG_PANEL, foreground="#888ea8", padding=[18, 8], font=("Arial", 10, "bold"), borderwidth=0)
        self.style.map("TNotebook.Tab", background=[("selected", self.NEON_BLUE)], foreground=[("selected", "#ffffff")])
        
        # Gaya untuk Frame Luaran & Labelframe (Panel Kontena Kotak)
        self.style.configure("TFrame", background=self.BG_MAIN)
        self.style.configure("Panel.TLabelframe", background=self.BG_PANEL, foreground=self.NEON_CYAN, borderwidth=1, relief="solid")
        self.style.configure("Panel.TLabelframe.Label", background=self.BG_PANEL, foreground=self.NEON_CYAN, font=("Arial", 10, "bold"))
        
        # Gaya Komponen Jadual (Treeview Gelap)
        self.style.configure("Treeview", background="#19233c", foreground=self.FG_TEXT, fieldbackground="#19233c", rowheight=28, font=("Arial", 9))
        self.style.configure("Treeview.Heading", background=self.BG_PANEL, foreground=self.NEON_CYAN, font=("Arial", 9, "bold"), borderwidth=1, relief="flat")
        self.style.map("Treeview", background=[("selected", "#253b5e")], foreground=[("selected", self.NEON_CYAN)])

        # Setup Notebook Tab Layout Utama
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.tab_attendance = ttk.Frame(self.notebook)
        self.tab_crud = ttk.Frame(self.notebook)
        self.tab_hours_check = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_attendance, text=" 📊 Log Kehadiran ")
        self.notebook.add(self.tab_crud, text=" 👤 Urus Profil & Laporan ")
        self.notebook.add(self.tab_hours_check, text=" ⏱️ Semak Jam Kerja ")
        
        # Bina isi kandungan setiap Tab (Bahagian A, B, dan C)
        self.setup_attendance_tab()
        self.setup_crud_tab()
        self.setup_hours_check_tab()

        # Janakan Treeview / Jadual Data bagi setiap Tab
        self.tree_attendance = self.create_treeview_widget(self.tab_attendance, show_all_cols=True)
        self.tree_crud = self.create_treeview_widget(self.tab_crud, show_all_cols=False) 
        self.tree_hours = self.create_treeview_widget(self.tab_hours_check, show_all_cols=True)
        
        self.tree_crud.bind("<<TreeviewSelect>>", self.get_selected_row_data)
        self.refresh_table()

        self.add_exit_button(self.tab_attendance)
    
    def add_exit_button(self, parent_frame):
        frame_footer = tk.Frame(parent_frame, bg="#0e1726", pady=10)
        frame_footer.pack(fill="x", side="bottom")
        
        btn_exit = tk.Button(
            frame_footer, text="EXIT SYSTEM", font=("Arial", 10, "bold"), 
            bg="#ff4d4d", fg="white", command=self.confirm_exit,
            cursor="hand2", padx=20
        )
        btn_exit.pack(side="right", padx=20)

    def confirm_exit(self):
        if messagebox.askyesno("Exit", "Adakah anda pasti mahu keluar dari sistem?"):
            self.root.destroy()

    # -------------------------------------------------------------------------
    # PART A: LOG KEHADIRAN (TAB 1)
    # -------------------------------------------------------------------------
    def setup_attendance_tab(self):
        f = ttk.LabelFrame(self.tab_attendance, text=" PENGURUSAN LOG KEHADIRAN AKTIF ", style="Panel.TLabelframe", padding=15)
        f.pack(fill="x", padx=15, pady=10)
        
        # Baris 1: ID Input & Clock In Out
        r1 = tk.Frame(f, bg=self.BG_PANEL)
        r1.pack(fill="x", pady=(5, 15))
        
        tk.Label(r1, text="Masukkan ID Pekerja:", font=("Arial", 11), bg=self.BG_PANEL, fg=self.FG_TEXT).pack(side="left", padx=5)
        self.ent_clock_id = tk.Entry(r1, font=("Arial", 11), width=18, bg="#0e1726", fg=self.NEON_CYAN, insertbackground="white", bd=1, relief="solid")
        self.ent_clock_id.pack(side="left", padx=(5, 20))
        
        btn_in = tk.Button(r1, text="🟢 Clock In", font=("Arial", 10, "bold"), bg="#102a45", fg=self.NEON_GREEN, activebackground=self.NEON_GREEN, bd=1, relief="flat", command=self.action_clock_in, padx=12, pady=2)
        btn_in.pack(side="left", padx=5)
        
        btn_out = tk.Button(r1, text="🔴 Clock Out", font=("Arial", 10, "bold"), bg="#3d1d28", fg=self.NEON_RED, activebackground=self.NEON_RED, bd=1, relief="flat", command=self.action_clock_out, padx=12, pady=2)
        btn_out.pack(side="left", padx=5)
        
        # Baris 2: Sistem Tapisan Kalendar Tarikh
        r2 = tk.Frame(f, bg=self.BG_PANEL)
        r2.pack(fill="x", pady=(0, 5))
        
        tk.Label(r2, text="Semak Tarikh (YYYY-MM-DD):", font=("Arial", 10, "bold"), bg=self.BG_PANEL, fg=self.FG_TEXT).pack(side="left", padx=5)
        self.ent_check_date = tk.Entry(r2, font=("Arial", 10), width=15, bg="#0e1726", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        self.ent_check_date.pack(side="left", padx=10)
        self.ent_check_date.insert(0, datetime.now().strftime("%Y-%m-%d")) 
        
        btn_semak = tk.Button(r2, text="🔍 Semak", font=("Arial", 9, "bold"), bg="#0e1726", fg=self.NEON_CYAN, bd=1, relief="solid", command=self.action_filter_attendance_by_date, padx=8)
        btn_semak.pack(side="left", padx=5)
        
        btn_refresh = tk.Button(r2, text="🔄 Papar Semua", font=("Arial", 9, "bold"), bg="#0e1726", fg="#ffffff", bd=1, relief="solid", command=lambda: self.refresh_table(), padx=8)
        btn_refresh.pack(side="left", padx=5)
        
        btn_delete = tk.Button(r2, text="🗑️ Padam Log", font=("Arial", 9, "bold"), bg="#3d1d28", fg=self.NEON_RED, bd=1, relief="solid", command=self.action_delete_selected_log, padx=8)
        btn_delete.pack(side="right", padx=5)
        
        tk.Label(self.tab_attendance, text="Senarai Log Rekod Kehadiran Pekerja:", font=("Arial", 11, "bold"), bg=self.BG_MAIN, fg=self.NEON_CYAN).pack(anchor="w", padx=15, pady=(15, 0))

    # -------------------------------------------------------------------------
    # PART B: URUS PROFIL & LAPORAN - CRUD (TAB 2)
    # -------------------------------------------------------------------------
    def setup_crud_tab(self):
        form = ttk.LabelFrame(self.tab_crud, text=" BORANG PENGURUSAN DATA MAKLUMAT PEKERJA ", style="Panel.TLabelframe", padding=15)
        form.pack(fill="x", padx=15, pady=10)
        
        p_form = tk.Frame(form, bg=self.BG_PANEL)
        p_form.pack(fill="x")
        
        self.ent_id = tk.Entry(p_form, bg="#0e1726", fg="#ffffff", insertbackground="white", bd=1, relief="solid", width=22, font=("Arial", 10))
        self.ent_name = tk.Entry(p_form, bg="#0e1726", fg="#ffffff", insertbackground="white", bd=1, relief="solid", width=38, font=("Arial", 10))
        self.cb_dept = ttk.Combobox(p_form, values=["Pentadbiran", "Kejuruteraan", "Sumber Manusia", "IT & Teknikal"], state="readonly", width=25)
        self.cb_dept.current(0)
        
        # Grid Aturan Borang Input Maklumat Pekerja
        tk.Label(p_form, text="ID Baru / Sedia Ada:", font=("Arial", 10), bg=self.BG_PANEL, fg="#ffffff").grid(row=0, column=0, sticky="w", padx=5, pady=6)
        self.ent_id.grid(row=0, column=1, padx=10, pady=6, sticky="w")
        
        tk.Label(p_form, text="Nama Penuh Pekerja:", font=("Arial", 10), bg=self.BG_PANEL, fg="#ffffff").grid(row=1, column=0, sticky="w", padx=5, pady=6)
        self.ent_name.grid(row=1, column=1, padx=10, pady=6, sticky="w")
        
        tk.Label(p_form, text="Pilihan Jabatan/Sektor:", font=("Arial", 10), bg=self.BG_PANEL, fg="#ffffff").grid(row=2, column=0, sticky="w", padx=5, pady=6)
        self.cb_dept.grid(row=2, column=1, padx=10, pady=6, sticky="w")
            
        # Kotak Panel Butang-butang Kendalian CRUD
        b_frame = tk.Frame(self.tab_crud, bg=self.BG_MAIN)
        b_frame.pack(fill="x", padx=15, pady=8)
        
        btn_cfg = [
            ("➕ Daftar Pekerja", self.NEON_GREEN, self.action_create),
            ("✏️ Kemaskini Profil", self.NEON_BLUE, self.action_update),
            ("❌ Padam Pekerja", self.NEON_RED, self.action_delete),
            ("🧹 Kosongkan Borang", "#ffffff", self.clear_entries)
        ]
        for t, color, cmd in btn_cfg:
            tk.Button(b_frame, text=t, font=("Arial", 9, "bold"), bg=self.BG_PANEL, fg=color, activebackground=color, bd=1, relief="solid", command=cmd, padx=12, pady=4).pack(side="left", padx=5)
            
        # Garis neon pemisah visual
        sep = tk.Frame(self.tab_crud, height=1, bg="#253b5e")
        sep.pack(fill='x', padx=15, pady=12)
        
        # Sektor Eksport / Import Fail Pangkalan Data
        r_frame = tk.Frame(self.tab_crud, bg=self.BG_MAIN)
        r_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Button(r_frame, text="📥 Eksport Laporan (CSV/TXT)", font=("Arial", 9, "bold"), bg="#102a45", fg=self.NEON_CYAN, bd=1, relief="solid", command=self.action_export_report_file, padx=14, pady=6).pack(side="left")
        tk.Button(r_frame, text="📂 Import Data Lama (TXT/CSV)", font=("Arial", 9, "bold"), bg="#102a45", fg="#ffffff", bd=1, relief="solid", command=self.action_import_old_data, padx=14, pady=6).pack(side="left", padx=12)
        
        tk.Label(self.tab_crud, text="Pangkalan Data Keseluruhan Profil Pekerja Terdaftar:", font=("Arial", 11, "bold"), bg=self.BG_MAIN, fg=self.NEON_CYAN).pack(anchor="w", padx=15, pady=(15, 0))

    # -------------------------------------------------------------------------
    # PART C: SEMAK JAM KERJA (TAB 3)
    # -------------------------------------------------------------------------
    def setup_hours_check_tab(self):
        f = ttk.LabelFrame(self.tab_hours_check, text=" SISTEM KALKULATOR JUMLAH JAM BEKERJA ACUMULATED ", style="Panel.TLabelframe", padding=15)
        f.pack(fill="x", padx=15, pady=10)
        h_ini = datetime.now().strftime("%Y-%m-%d")
        
        p_grid = tk.Frame(f, bg=self.BG_PANEL)
        p_grid.pack(fill="x")
        
        tk.Label(p_grid, text="Masukkan ID Pekerja:", font=("Arial", 10, "bold"), bg=self.BG_PANEL, fg=self.FG_TEXT).grid(row=0, column=0, padx=5, pady=6, sticky="w")
        self.ent_search_emp_id = tk.Entry(p_grid, font=("Arial", 10), width=15, bg="#0e1726", fg=self.NEON_CYAN, insertbackground="white", bd=1, relief="solid")
        self.ent_search_emp_id.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        
        self.ent_start_date = tk.Entry(p_grid, font=("Arial", 10), width=14, bg="#0e1726", fg="#ffffff", bd=1, relief="solid")
        self.ent_end_date = tk.Entry(p_grid, font=("Arial", 10), width=14, bg="#0e1726", fg="#ffffff", bd=1, relief="solid")
        
        tk.Label(p_grid, text="Tarikh Awal (Mula):", font=("Arial", 10), bg=self.BG_PANEL, fg="#ffffff").grid(row=1, column=0, padx=5, pady=6, sticky="w")
        self.ent_start_date.grid(row=1, column=1, padx=8, pady=6, sticky="w")
        self.ent_start_date.insert(0, h_ini)
        
        tk.Label(p_grid, text="Tarikh Akhir (Tamat):", font=("Arial", 10), bg=self.BG_PANEL, fg="#ffffff").grid(row=1, column=2, padx=15, pady=6, sticky="w")
        self.ent_end_date.grid(row=1, column=3, padx=8, pady=6, sticky="w")
        self.ent_end_date.insert(0, h_ini)
            
        btn_calc = tk.Button(p_grid, text="⚡ Hitung Jam Kerja", font=("Arial", 10, "bold"), bg="#102a45", fg=self.NEON_CYAN, bd=1, relief="solid", command=self.action_calculate_employee_hours, padx=12, pady=2)
        btn_calc.grid(row=1, column=4, padx=25, pady=6)
        
        # Papan Skor Digital paparan Jumlah Jam
        self.lbl_total_calc = tk.Label(p_grid, text="Jumlah Jam Terkumpul Pekerja: 0.00 jam", font=("Arial", 11, "bold"), bg=self.BG_PANEL, fg=self.NEON_GREEN)
        self.lbl_total_calc.grid(row=0, column=2, columnspan=3, padx=15, pady=6, sticky="w")
        
        tk.Label(self.tab_hours_check, text="Hasil Tapisan Papan Log Jam Kerja Sesi:", font=("Arial", 11, "bold"), bg=self.BG_MAIN, fg=self.NEON_CYAN).pack(anchor="w", padx=15, pady=(15, 0))

    # -------------------------------------------------------------------------
    # KOMPONEN UTILIITI (JADUAL TREEVIEW & LOGIK FRONTEND)
    # -------------------------------------------------------------------------
    def create_treeview_widget(self, parent, show_all_cols=True):
        f = ttk.Frame(parent)
        f.pack(fill="both", expand=True, padx=15, pady=10)
        
        cols = {"id": ("ID Pekerja", 90, "center"), "name": ("Nama Pekerja", 200, "w"), "dept": ("Jabatan", 140, "center"), "status": ("Status Sesi", 90, "center"), "time_in": ("Masa Clock In", 150, "center"), "time_out": ("Masa Clock Out", 150, "center"), "hours": ("Jam (jam)", 110, "center")} if show_all_cols else {"id": ("ID Pekerja", 120, "center"), "name": ("Nama Pekerja", 280, "w"), "dept": ("Jabatan", 200, "center")}
        
        tree = ttk.Treeview(f, columns=list(cols.keys()), show="headings")
        for k, v in cols.items(): 
            tree.heading(k, text=v[0])
            tree.column(k, width=v[1], anchor=v[2])
            
        sb = ttk.Scrollbar(f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    def parse_datetime_flexible(self, text):
        if not text or text.strip() in ["-", ""]: return datetime.min
        try: return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError: return datetime.min

    def refresh_table(self):
        for tree in [self.tree_attendance, self.tree_crud, self.tree_hours]:
            for item in tree.get_children(): tree.delete(item)
            
        sorted_logs = sorted(self.system.all_logs, key=lambda e: (e.id.upper(), self.parse_datetime_flexible(e.last_clock_in)))
        for emp in sorted_logs:
            if emp.last_clock_in != "-":
                self.tree_attendance.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))
                self.tree_hours.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))

        seen_worker_ids = set()
        unique_workers = []
        for emp in reversed(self.system.all_logs):
            if emp.id.upper() not in seen_worker_ids:
                seen_worker_ids.add(emp.id.upper()); unique_workers.append(emp)
                
        for emp in sorted(unique_workers, key=lambda e: e.id.upper()):
            self.tree_crud.insert("", "end", values=(emp.id, emp.name, emp.department))

    def action_delete_selected_log(self):
        if not (selected := self.tree_attendance.selection()): return messagebox.showwarning("Amaran", "Sila klik baris log!")
        v = self.tree_attendance.item(selected[0], "values")
        if v[4] == "-": return messagebox.showwarning("Amaran", "Profil asas tidak boleh dipadam di sini.")
        if messagebox.askyesno("Sahkan", f"Padam log selected?"):
            success, msg = self.system.delete_specific_log(v[0], v[4])
            messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
            self.refresh_table()

    def action_import_old_data(self):
        if pilihan := filedialog.askopenfilename(filetypes=[("Supported Files", "*.txt;*.csv")], title="Pilih Fail Lama"):
            success, msg = self.system.import_old_data_file(pilihan)
            messagebox.showinfo("Import", msg) if success else messagebox.showerror("Ralat", msg)
            self.refresh_table()

    def action_export_report_file(self):
        if filepath := filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")], title="Eksport Laporan"):
            success, msg = self.system.export_all_data_to_file(filepath)
            messagebox.showinfo("Eksport", msg) if success else messagebox.showerror("Ralat", msg)

    def action_filter_attendance_by_date(self):
        d_str = self.ent_check_date.get().strip()
        try: datetime.strptime(d_str, "%Y-%m-%d")
        except ValueError: return messagebox.showerror("Ralat", "Format tarikh wajib YYYY-MM-DD!")
        for item in self.tree_attendance.get_children(): self.tree_attendance.delete(item)
        
        match_logs = [e for e in self.system.all_logs if e.last_clock_in.startswith(d_str)]
        for emp in sorted(match_logs, key=lambda e: (e.id.upper(), self.parse_datetime_flexible(e.last_clock_in))):
            self.tree_attendance.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))

    def get_selected_row_data(self, event):
        if (selected := self.tree_crud.selection()) and (v := self.tree_crud.item(selected[0], "values")):
            self.clear_entries()
            self.ent_id.insert(0, v[0])
            self.ent_name.insert(0, v[1])
            if v[2] in self.cb_dept['values']: self.cb_dept.set(v[2])

    def action_calculate_employee_hours(self):
        t_id, t_awal, t_akhir = self.ent_search_emp_id.get().strip().upper(), self.ent_start_date.get().strip(), self.ent_end_date.get().strip()
        try: d_awal, d_akhir = datetime.strptime(t_awal, "%Y-%m-%d").date(), datetime.strptime(t_akhir, "%Y-%m-%d").date()
        except ValueError: return messagebox.showerror("Ralat", "Format tarikh wajib YYYY-MM-DD!")
        for item in self.tree_hours.get_children(): self.tree_hours.delete(item)
        
        valid_logs = [e for e in self.system.all_logs if e.id.upper() == t_id and e.last_clock_in != "-" and d_awal <= self.parse_datetime_flexible(e.last_clock_in).date() <= d_akhir]
        for emp in valid_logs: self.tree_hours.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))
        self.lbl_total_calc.config(text=f"Jumlah Jam [{t_id}]: {sum(float(e.total_hours) for e in valid_logs):.2f} jam" if valid_logs else "Jumlah Jam Terkumpul: 0.00 jam")

    def action_clock_in(self):
        if not self.ent_clock_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Pekerja!")
        success, msg = self.system.clock_in_employee(self.ent_clock_id.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
        self.ent_clock_id.delete(0, tk.END)
        self.refresh_table()

    def action_clock_out(self):
        if not self.ent_clock_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Pekerja!")
        success, msg = self.system.clock_out_employee(self.ent_clock_id.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
        self.ent_clock_id.delete(0, tk.END)
        self.refresh_table()

    def action_create(self):
        if not self.ent_id.get().strip() or not self.ent_name.get().strip(): return messagebox.showwarning("Amaran", "Isi ID dan Nama!")
        success, msg = self.system.create_employee(self.ent_id.get(), self.ent_name.get(), self.cb_dept.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
        self.clear_entries()
        self.refresh_table()

    def action_update(self):
        if not self.ent_id.get().strip() or not self.ent_name.get().strip(): return messagebox.showwarning("Amaran", "Isi ID dan Nama!")
        success, msg = self.system.update_employee(self.ent_id.get(), self.ent_name.get(), self.cb_dept.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
        self.clear_entries()
        self.refresh_table()

    def action_delete(self):
        if not self.ent_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Profil!")
        if messagebox.askyesno("Sahkan", f"Padam semua rekod profil {self.ent_id.get()}?"):
            success, msg = self.system.delete_employee(self.ent_id.get())
            messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
            self.clear_entries()
            self.refresh_table()

    def clear_entries(self):
        self.ent_id.delete(0, tk.END)
        self.ent_name.delete(0, tk.END)
        self.cb_dept.current(0)

# =========================================================================
# 3. FUNGSI SPLASH SCREEN (PAPARAN GAMBAR SEBELUM GUI MENU UTAMA)
# =========================================================================
class LoginScreen:
    """Paparan Log Masuk berciri Cyberpunk Neon sebelum akses Menu Utama"""
    def __init__(self, root, on_success_callback, path_background=None):
        self.root = root
        self.on_success_callback = on_success_callback
        self.root.title("AURA Attendance System - Security Login")
        window_width = 450
        window_height = 500
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.configure(bg="#0e1726")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
        main_frame = tk.Frame(self.root, bg="#1b2e4b", bd=2, relief="solid", highlightbackground="#00f2fe", highlightcolor="#00f2fe")
        main_frame.place(relx=0.5, rely=0.5, anchor="center", width=380, height=430)
        
        # Sokongan Imej Logo/Pengepala dari screenshot potong kotak login
        if path_background and os.path.exists(path_background):
            try:
                img = Image.open(path_background).resize((100, 100), Image.Resampling.LANCZOS)
                self.img_tk = ImageTk.PhotoImage(img)
                lbl_logo = tk.Label(main_frame, image=self.img_tk, bg="#1b2e4b")
                lbl_logo.pack(pady=(20, 5))
            except Exception:
                self.draw_default_text_logo(main_frame)
        else:
            self.draw_default_text_logo(main_frame)
        # Papan Input Username
        tk.Label(main_frame, text="Admin Username", font=("Arial", 11, "bold"), bg="#1b2e4b", fg="#00f2fe").pack(anchor="w", padx=40, pady=(15, 2))
        self.ent_user = tk.Entry(main_frame, font=("Arial", 12), bg="#0e1726", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        self.ent_user.pack(fill="x", padx=40, ipady=4)
        self.ent_user.insert(0, "admin")  # Set sebagai nilai lalai seperti dalam imej
        # Papan Input Password
        tk.Label(main_frame, text="Admin Password", font=("Arial", 11, "bold"), bg="#1b2e4b", fg="#00f2fe").pack(anchor="w", padx=40, pady=(15, 2))
        self.ent_pass = tk.Entry(main_frame, font=("Arial", 12), bg="#0e1726", fg="#ffffff", insertbackground="white", bd=1, relief="solid", show="●")
        self.ent_pass.pack(fill="x", padx=40, ipady=4)
        self.ent_pass.bind("<Return>", lambda event: self.semak_katalaluan())
        # Butang LOGIN bercahaya perak/neon
        btn_login = tk.Button(main_frame, text="LOGIN", font=("Arial", 12, "bold"), bg="#a0aab5", fg="#0e1726", activebackground="#00f2fe", bd=0, command=self.semak_katalaluan, cursor="hand2")
        btn_login.pack(fill="x", padx=40, pady=(35, 10), ipady=6)

    def draw_default_text_logo(self, parent):
        tk.Label(parent, text="▲ AURA", font=("Arial", 26, "bold"), bg="#1b2e4b", fg="#ffffff").pack(pady=(30, 5))
        tk.Label(parent, text="MANAGEMENT SECURITY", font=("Arial", 8), bg="#1b2e4b", fg="#00f2fe").pack()

    def semak_katalaluan(self):
        u, p = self.ent_user.get().strip(), self.ent_pass.get().strip()
        # Hardcoded kelayakan masuk (Boleh ditukar mengikut kesesuaian)
        if u == "admin" and p == "admin123":
            messagebox.showinfo("Akses Diterima", "Selamat Datang Kembali, Pentadbir AURA System.")
            self.on_success_callback() # Panggil menu utama
        else:
            messagebox.showerror("Akses Ditolak", "Username atau Password salah! Sila cuba lagi.")
            self.ent_pass.delete(0, tk.END)

def tunjuk_splash_screen(root_utama, path_gambar, masa_papar=3000):
    if not os.path.exists(path_gambar):
        print(f"Nota: Fail gambar '{path_gambar}' tidak dijumpai. Splash screen dilangkau.")
        return
    splash = tk.Toplevel()
    splash.title("Memuatkan Sistem...")
    splash.overrideredirect(True)
    try:
        img_asal = Image.open(path_gambar)
        # Menukar saiz poster jika terlalu besar untuk skrin komputer riba biasa
        img_asal = img_asal.resize((800, 550), Image.Resampling.LANCZOS)
        lebar_img, tinggi_img = img_asal.size
        lebar_skrin = splash.winfo_screenwidth()
        tinggi_skrin = splash.winfo_screenheight()
        posisi_x = int((lebar_skrin / 2) - (lebar_img / 2))
        posisi_y = int((tinggi_skrin / 2) - (tinggi_img / 2))
        splash.geometry(f"{lebar_img}x{tinggi_img}+{posisi_x}+{posisi_y}")
        img_tk = ImageTk.PhotoImage(img_asal)
        lbl_gambar = tk.Label(splash, image=img_tk, bd=0)
        lbl_gambar.image = img_tk  
        lbl_gambar.pack()
        splash.update()
        root_utama.withdraw() # Sembunyikan seketika tetingkap utama semasa splash berjalan
        root_utama.after(masa_papar, splash.destroy)
    except Exception as e:
        print(f"Ralat Splash: {e}")
        splash.destroy()

# =========================================================================
# 4. SISTEM UTAMA DRIVER RUNNER
# =========================================================================
def lancarkan_menu_utama():
    """Fungsi callback yang dipanggil apabila pengesahan login berjaya"""
    global app_gui
    for widget in root.winfo_children(): widget.destroy()
    root.deiconify()
    root.geometry("1100x750")
    root.resizable(True, True)
    app_gui = AttendanceGUI(root, core_system)

if __name__ == "__main__":
    core_system = AttendanceSystem("attendance_data.txt")
    root = tk.Tk()
    root.withdraw()
    # Konfigurasi Aset
    POSTER, LOGIN_BG = "Attandance_System.jpg", "Screenshot 2026-06-06 134243.png"
    # Jalankan Splash Screen
    tunjuk_splash_screen(root, POSTER, masa_papar=3000)
    # Aliran Pelancaran: Splash -> Login -> Dashboard
    root.after(3100, lambda: [root.deiconify(), LoginScreen(root, lancarkan_menu_utama, LOGIN_BG)])
    root.mainloop()