import os, csv, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# =========================================================================
# 1. STRUKTUR DATA (BACKEND)
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
        """Muat data dari fail teks utama semasa app dibuka"""
        if not os.path.exists(self.filename):
            if not (pilihan := filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")], title="Pilih Fail Data Kehadiran")): return
            self.filename = pilihan
        try:
            with open(self.filename, "r") as f: 
                for line in f:
                    if line.strip():
                        parts = [p.strip() for p in line.strip().split("|")]
                        if len(parts) >= 3:
                            clean_parts = parts + ["-"] * (7 - len(parts))
                            if clean_parts[6] == "-": clean_parts[6] = "0.00"
                            self.all_logs.append(Employee(*clean_parts[:7]))
        except Exception as e: messagebox.showerror("Ralat", f"Gagal membaca fail: {e}")

    def standardize_datetime(self, date_str):
        """Seragamkan pelbagai format tarikh ke format standard YYYY-MM-DD HH:MM:SS"""
        if not date_str or date_str.strip() in ["-", ""]: return "-"
        date_str = date_str.strip()
        if date_str.startswith('="') and date_str.endswith('"'): date_str = date_str[2:-1].strip()
        date_str = date_str.replace("\t", "").strip()
        
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M"]:
            try: return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError: continue
        return date_str

    def import_old_data_file(self, filepath):
        """Import data lama (.txt/.csv) tanpa masukkan rekod bertindih (anti-duplikasi)"""
        count = 0
        try:
            existing_records = {(emp.id.upper(), emp.last_clock_in) for emp in self.all_logs if emp.last_clock_in != "-"}
            existing_profiles = {emp.id.upper() for emp in self.all_logs}
            rows = []
            
            if filepath.endswith('.txt'):
                with open(filepath, "r") as f: rows = [line.strip().split("|") for line in f if line.strip()]
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
        """Padam satu baris log kehadiran yang dipilih"""
        orig_len = len(self.all_logs)
        self.all_logs = [e for e in self.all_logs if not (e.id.upper() == emp_id.strip().upper() and e.last_clock_in == clock_in_time)]
        return (self.rewrite_all_data() or (True, "Log berjaya dipadam.")) if len(self.all_logs) < orig_len else (False, "Log tidak ditemui!")

    def get_latest_status(self, emp_id):
        """Dapatkan status terakhir pekerja (Present/Absent)"""
        return next((e for e in reversed(self.all_logs) if e.id.upper() == emp_id.strip().upper()), None)

    def clock_in_employee(self, emp_id):
        """Proses mendaftar masuk (Clock In) pekerja"""
        if not (latest := self.get_latest_status(emp_id)): return False, "ID belum didaftarkan!"
        if latest.status == "Present": return False, "Pekerja sudah Clock In!"
        
        new_log = Employee(emp_id.strip().upper(), latest.name, latest.department, "Present", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-", "0.00")
        self.all_logs.append(new_log)
        try:
            with open(self.filename, "a") as f: f.write(f"{new_log.id}|{new_log.name}|{new_log.department}|{new_log.status}|{new_log.last_clock_in}|{new_log.last_clock_out}|{new_log.total_hours}\n")
            return True, f"Clock In Berjaya! Selamat bekerja, {latest.name}."
        except Exception as e: return False, f"Gagal menulis fail: {e}"

    def clock_out_employee(self, emp_id):
        """Proses mendaftar keluar (Clock Out) dan mengira jam bekerja"""
        if not (latest := self.get_latest_status(emp_id)) or latest.status == "Absent" or latest.last_clock_in == "-": return False, "Perlu Clock In dahulu!"
        
        now = datetime.now()
        latest.last_clock_out, latest.status = now.strftime("%Y-%m-%d %H:%M:%S"), "Absent"
        latest.total_hours = f"{(now - datetime.strptime(latest.last_clock_in, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600:.2f}"
        self.rewrite_all_data() 
        return True, f"Clock Out Berjaya! Masa: {latest.total_hours} jam."

    def create_employee(self, emp_id, name, department):
        """Daftar profil asas pekerja baru (Sistem CRUD)"""
        if self.get_latest_status(emp_id): return False, "ID sudah wujud!"
        new_emp = Employee(emp_id.strip().upper(), name.strip(), department)
        self.all_logs.append(new_emp)
        try:
            with open(self.filename, "a") as f: f.write(f"{new_emp.id}|{new_emp.name}|{new_emp.department}|{new_emp.status}|{new_emp.last_clock_in}|{new_emp.last_clock_out}|{new_emp.total_hours}\n")
            return True, "Pekerja berjaya didaftarkan."
        except Exception as e: return False, f"Gagal mendaftar: {e}"

    def update_employee(self, emp_id, new_name, new_dept):
        """Kemaskini maklumat nama/jabatan pada semua rekod log pekerja"""
        found = False
        for e in self.all_logs:
            if e.id.upper() == emp_id.strip().upper(): e.name, e.department, found = new_name, new_dept, True
        if found: self.rewrite_all_data(); return True, "Profil berjaya dikemaskini."
        return False, "ID tidak ditemui!"

    def delete_employee(self, emp_id):
        """Padam terus semua profil dan keseluruhan sejarah log pekerja tersebut"""
        orig_len = len(self.all_logs)
        self.all_logs = [e for e in self.all_logs if e.id.upper() != emp_id.strip().upper()]
        if len(self.all_logs) < orig_len: self.rewrite_all_data(); return True, "Semua rekod pekerja dipadam."
        return False, "ID tidak ditemui!"

    def rewrite_all_data(self):
        """Tulis semula semua data terkini dari memori (RAM) ke fail teks"""
        try:
            with open(self.filename, "w") as f:
                for e in self.all_logs: f.write(f"{e.id}|{e.name}|{e.department}|{e.status}|{e.last_clock_in}|{e.last_clock_out}|{e.total_hours}\n")
        except Exception as e: messagebox.showerror("Ralat", f"Gagal kemaskini fail: {e}")

    def export_all_data_to_file(self, filepath):
        """Eksport laporan data ke fail luar (.csv / .txt)"""
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
# 2. ANTARAMUKA PENGGUNA (FRONTEND GUI)
# =========================================================================

class AttendanceGUI:
    """Menguruskan paparan tetingkap aplikasi (Tkinter GUI)"""
    def __init__(self, root, system):
        self.root, self.system = root, system
        root.title("Sistem Kehadiran Pekerja")
        root.geometry("1000x700")
        ttk.Style().theme_use("clam") 
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_attendance = ttk.Frame(self.notebook)
        self.tab_crud = ttk.Frame(self.notebook)
        self.tab_hours_check = ttk.Frame(self.notebook)
        
        for tab, text in zip([self.tab_attendance, self.tab_crud, self.tab_hours_check], [" Log Kehadiran ", " Urus Profil & Laporan ", " Semak Jam Kerja "]):
            self.notebook.add(tab, text=text)
            
        self.setup_attendance_tab()
        self.setup_crud_tab()
        self.setup_hours_check_tab()

        self.tree_attendance = self.create_treeview_widget(self.tab_attendance, show_all_cols=True)
        self.tree_crud = self.create_treeview_widget(self.tab_crud, show_all_cols=False) 
        self.tree_hours = self.create_treeview_widget(self.tab_hours_check, show_all_cols=True)
        
        self.tree_crud.bind("<<TreeviewSelect>>", self.get_selected_row_data)
        self.refresh_table()

    def setup_attendance_tab(self):
        """Bina butang Clock In/Out dan penapis tarikh pada Tab 1"""
        f = ttk.LabelFrame(self.tab_attendance, text="Sila Log Kehadiran", padding=15); f.pack(fill="x", padx=15, pady=10)
        r1 = ttk.Frame(f); r1.pack(fill="x", pady=(5, 15))
        ttk.Label(r1, text="Masukkan ID Pekerja:", font=("Arial", 11)).pack(side="left", padx=5)
        self.ent_clock_id = ttk.Entry(r1, font=("Arial", 11), width=18); self.ent_clock_id.pack(side="left", padx=(0, 20))
        ttk.Button(r1, text="Clock In", command=self.action_clock_in).pack(side="left", padx=5)
        ttk.Button(r1, text="Clock Out", command=self.action_clock_out).pack(side="left", padx=5)
        
        r2 = ttk.Frame(f); r2.pack(fill="x", pady=(0, 5))
        ttk.Label(r2, text="Semak Tarikh (YYYY-MM-DD):", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.ent_check_date = ttk.Entry(r2, font=("Arial", 10), width=15); self.ent_check_date.pack(side="left", padx=10)
        self.ent_check_date.insert(0, datetime.now().strftime("%Y-%m-%d")) 
        
        ttk.Button(r2, text="🔍 Semak", command=self.action_filter_attendance_by_date).pack(side="left", padx=5)
        ttk.Button(r2, text="🔄 Papar Semua", command=lambda: self.refresh_table()).pack(side="left", padx=5)
        ttk.Button(r2, text="🗑️ Padam Log", command=self.action_delete_selected_log).pack(side="right", padx=5)
        ttk.Label(self.tab_attendance, text="Senarai Log Rekod Kehadiran Pekerja:", font=("Arial", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 0))

    def setup_hours_check_tab(self):
        """Bina borang pengiraan julat jam bekerja pekerja pada Tab 3"""
        f = ttk.LabelFrame(self.tab_hours_check, text=" Semak & Hitung Jam Kerja ", padding=15); f.pack(fill="x", padx=15, pady=10)
        h_ini = datetime.now().strftime("%Y-%m-%d")
        
        ttk.Label(f, text="Masukkan ID Pekerja:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ent_search_emp_id = ttk.Entry(f, font=("Arial", 10), width=15); self.ent_search_emp_id.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.ent_start_date, self.ent_end_date = ttk.Entry(f, font=("Arial", 10), width=12), ttk.Entry(f, font=("Arial", 10), width=12)
        for i, (lbl, ent) in enumerate([("Tarikh Awal:", self.ent_start_date), ("Tarikh Akhir:", self.ent_end_date)]):
            ttk.Label(f, text=lbl).grid(row=1, column=i*2, padx=5, pady=5, sticky="w")
            ent.insert(0, h_ini); ent.grid(row=1, column=i*2+1, padx=5, pady=5, sticky="w")
            
        ttk.Button(f, text="Kira Jam", command=self.action_calculate_employee_hours).grid(row=1, column=4, padx=15, pady=5)
        self.lbl_total_calc = ttk.Label(f, text="Jumlah Jam Terkumpul Pekerja: 0.00 jam", font=("Arial", 11, "bold"), foreground="green")
        self.lbl_total_calc.grid(row=0, column=2, columnspan=3, padx=15, pady=5, sticky="w")
        ttk.Label(self.tab_hours_check, text="Hasil Tapisan Log Jam Kerja:", font=("Arial", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 0))

    def setup_crud_tab(self):
        """Bina borang pendaftaran, butang CRUD, serta import/eksport pada Tab 2"""
        form = ttk.LabelFrame(self.tab_crud, text="Borang Profil Pekerja Baru", padding=15); form.pack(fill="x", padx=15, pady=10)
        self.ent_id, self.ent_name = ttk.Entry(form), ttk.Entry(form, width=30)
        self.cb_dept = ttk.Combobox(form, values=["Pentadbiran", "Kejuruteraan", "Sumber Manusia", "IT & Teknikal"], state="readonly")
        self.cb_dept.current(0)
        
        for i, (text, widget) in enumerate([("ID Baru:", self.ent_id), ("Nama Penuh:", self.ent_name), ("Jabatan:", self.cb_dept)]):
            ttk.Label(form, text=text).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            widget.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            
        b_frame = ttk.Frame(self.tab_crud); b_frame.pack(fill="x", padx=15, pady=5)
        for t, cmd in [("Daftar Pekerja", self.action_create), ("Kemaskini Profil", self.action_update), ("Padam Pekerja", self.action_delete), ("Kosongkan Borang", self.clear_entries)]:
            ttk.Button(b_frame, text=t, command=cmd).pack(side="left", padx=5)
            
        ttk.Separator(self.tab_crud, orient='horizontal').pack(fill='x', padx=15, pady=10)
        r_frame = ttk.Frame(self.tab_crud); r_frame.pack(fill="x", padx=15, pady=5)
        ttk.Button(r_frame, text="📥 Eksport Laporan (CSV/TXT)", command=self.action_export_report_file).pack(side="left", ipady=3)
        ttk.Button(r_frame, text="📂 Import Data Lama (TXT/CSV)", command=self.action_import_old_data).pack(side="left", padx=10, ipady=3)

    def create_treeview_widget(self, parent, show_all_cols=True):
        """Fungsi pembantu untuk hasilkan jadual lajur paparan (Treeview)"""
        f = ttk.Frame(parent); f.pack(fill="both", expand=True, padx=15, pady=10)
        cols = {"id": ("ID Pekerja", 80, "center"), "name": ("Nama Pekerja", 180, "w"), "dept": ("Jabatan", 120, "center"), "status": ("Status Sesi", 80, "center"), "time_in": ("Masa Clock In", 140, "center"), "time_out": ("Masa Clock Out", 140, "center"), "hours": ("Jam (jam)", 140, "center")} if show_all_cols else {"id": ("ID Pekerja", 100, "center"), "name": ("Nama Pekerja", 250, "w"), "dept": ("Jabatan", 180, "center")}
        tree = ttk.Treeview(f, columns=list(cols.keys()), show="headings")
        for k, v in cols.items(): tree.heading(k, text=v[0]); tree.column(k, width=v[1], anchor=v[2])
        sb = ttk.Scrollbar(f, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        return tree
    
    def parse_datetime_flexible(self, text):
        """Tukar string tarikh kepada objek datetime untuk susunan/isihan"""
        if not text or text.strip() in ["-", ""]: return datetime.min
        try: return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError: return datetime.min

    def refresh_table(self):
        """Isi semula jadual paparan GUI dengan data terkini pangkalan data"""
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
        """Butang padam log kehadiran tertentu yang dipilih"""
        if not (selected := self.tree_attendance.selection()): return messagebox.showwarning("Amaran", "Sila klik baris log!")
        v = self.tree_attendance.item(selected[0], "values")
        if v[4] == "-": return messagebox.showwarning("Amaran", "Profil asas tidak boleh dipadam di sini.")
        if messagebox.askyesno("Sahkan", f"Padam log selected?"):
            success, msg = self.system.delete_specific_log(v[0], v[4])
            messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg)
            self.refresh_table()

    def action_import_old_data(self):
        """Butang buka dialog fail untuk proses import data"""
        if pilihan := filedialog.askopenfilename(filetypes=[("Supported Files", "*.txt;*.csv")], title="Pilih Fail Lama"):
            success, msg = self.system.import_old_data_file(pilihan)
            messagebox.showinfo("Import", msg) if success else messagebox.showerror("Ralat", msg)
            self.refresh_table()

    def action_export_report_file(self):
        """Butang buka dialog simpan fail untuk operasi eksport laporan"""
        if filepath := filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")], title="Eksport Laporan"):
            success, msg = self.system.export_all_data_to_file(filepath)
            messagebox.showinfo("Eksport", msg) if success else messagebox.showerror("Ralat", msg)

    def action_filter_attendance_by_date(self):
        """Butang tapis jadual log berdasarkan input tarikh spesifik"""
        d_str = self.ent_check_date.get().strip()
        try: datetime.strptime(d_str, "%Y-%m-%d")
        except ValueError: return messagebox.showerror("Ralat", "Format tarikh wajib YYYY-MM-DD!")
        for item in self.tree_attendance.get_children(): self.tree_attendance.delete(item)
        
        match_logs = [e for e in self.system.all_logs if e.last_clock_in.startswith(d_str)]
        for emp in sorted(match_logs, key=lambda e: (e.id.upper(), self.parse_datetime_flexible(e.last_clock_in))):
            self.tree_attendance.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))

    def get_selected_row_data(self, event):
        """Klik baris jadual crud untuk isikan borang automatik"""
        if (selected := self.tree_crud.selection()) and (v := self.tree_crud.item(selected[0], "values")):
            self.clear_entries(); self.ent_id.insert(0, v[0]); self.ent_name.insert(0, v[1])
            if v[2] in self.cb_dept['values']: self.cb_dept.set(v[2])

    def action_calculate_employee_hours(self):
        """Butang hitung jumlah jam bekerja terkumpul pekerja mengikut julat tarikh"""
        t_id, t_awal, t_akhir = self.ent_search_emp_id.get().strip().upper(), self.ent_start_date.get().strip(), self.ent_end_date.get().strip()
        try: d_awal, d_akhir = datetime.strptime(t_awal, "%Y-%m-%d").date(), datetime.strptime(t_akhir, "%Y-%m-%d").date()
        except ValueError: return messagebox.showerror("Ralat", "Format tarikh wajib YYYY-MM-DD!")
        for item in self.tree_hours.get_children(): self.tree_hours.delete(item)
        
        valid_logs = [e for e in self.system.all_logs if e.id.upper() == t_id and e.last_clock_in != "-" and d_awal <= self.parse_datetime_flexible(e.last_clock_in).date() <= d_akhir]
        for emp in valid_logs: self.tree_hours.insert("", "end", values=(emp.id, emp.name, emp.department, emp.status, emp.last_clock_in, emp.last_clock_out, emp.total_hours))
        self.lbl_total_calc.config(text=f"Jumlah Jam [{t_id}]: {sum(float(e.total_hours) for e in valid_logs):.2f} jam" if valid_logs else "Jumlah Jam Terkumpul: 0.00 jam")

    def action_clock_in(self):
        """Butang mencetuskan log pendaftaran masuk kerja"""
        if not self.ent_clock_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Pekerja!")
        success, msg = self.system.clock_in_employee(self.ent_clock_id.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg); self.ent_clock_id.delete(0, tk.END); self.refresh_table()

    def action_clock_out(self):
        """Butang mencetuskan log pendaftaran keluar kerja"""
        if not self.ent_clock_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Pekerja!")
        success, msg = self.system.clock_out_employee(self.ent_clock_id.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg); self.ent_clock_id.delete(0, tk.END); self.refresh_table()

    def action_create(self):
        """Butang hantar arahan CRUD tambah pekerja baru"""
        if not self.ent_id.get().strip() or not self.ent_name.get().strip(): return messagebox.showwarning("Amaran", "Isi ID dan Nama!")
        success, msg = self.system.create_employee(self.ent_id.get(), self.ent_name.get(), self.cb_dept.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg); self.clear_entries(); self.refresh_table()

    def action_update(self):
        """Butang hantar arahan CRUD kemaskini profil pekerja"""
        if not self.ent_id.get().strip() or not self.ent_name.get().strip(): return messagebox.showwarning("Amaran", "Isi ID dan Nama!")
        success, msg = self.system.update_employee(self.ent_id.get(), self.ent_name.get(), self.cb_dept.get())
        messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg); self.clear_entries(); self.refresh_table()

    def action_delete(self):
        """Butang hantar arahan CRUD padam terus profil pekerja"""
        if not self.ent_id.get().strip(): return messagebox.showwarning("Amaran", "Isi ID Profil!")
        if messagebox.askyesno("Sahkan", f"Padam semua rekod profil {self.ent_id.get()}?"):
            success, msg = self.system.delete_employee(self.ent_id.get())
            messagebox.showinfo("Berjaya", msg) if success else messagebox.showerror("Ralat", msg); self.clear_entries(); self.refresh_table()

    def clear_entries(self):
        """Kosongkan ruangan input borang pada GUI"""
        self.ent_id.delete(0, tk.END); self.ent_name.delete(0, tk.END); self.cb_dept.current(0)


# =========================================================================
# 3. TITIK PERMULAAN SISTEM (MAIN ENTRY)
# =========================================================================
if __name__ == "__main__":
    root = tk.Tk()                                    
    app = AttendanceGUI(root, AttendanceSystem())     
    root.mainloop()