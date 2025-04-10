import os
import locale
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from tkinter.filedialog import asksaveasfilename
from datetime import datetime, timedelta
import openpyxl
import threading
import queue
import requests
import sys
#from subprocess import call, Popen  # No longer used for edit mode
from utils import load_veri2, get_max_name_length, ensure_files_exist, VERI1_PATH, VERI2_PATH, MASAUSTU_PATH, load_mesai_ucret
from data_processing import eksik_verileri_guncelle, process_data
from esp32 import ensure_valid_esp32_ip
from edit_mode import EditPanel   # Import the new EditPanel class

LOCAL_FOLDER = "Kayıtlar"
LOCAL_FILE_PATH = os.path.join(LOCAL_FOLDER, "veri2.txt")

personel_listesi = []
mesai_ucretleri = {}

def dosya_kontrol_et():
    """Kayıtlar klasörünü ve Personeller.txt dosyasını kontrol et"""
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)
        print("Kayıtlar klasörü oluşturuldu.")
    if not os.path.exists(LOCAL_FILE_PATH):
        with open(LOCAL_FILE_PATH, "w") as f:
            f.write("ID,Ad Soyad,Dogum Tarihi\n")
            print("Personeller.txt dosyası oluşturuldu.")

def dosya_kaydet():
    """Personel listesini dosyaya kaydet"""
    with open(LOCAL_FILE_PATH, "w") as f:
        for personel in personel_listesi:
            f.write(",".join(personel) + "\n")
    print("Personeller dosyası otomatik olarak güncellendi.")

def dosya_yukle():
    """Personeller dosyasını ESP32'ye gönder"""
    try:
        with open(LOCAL_FILE_PATH, "r") as f:
            data = f.read()
        response = requests.post(f"{ESP32_IP}/upload", data=data)
        if response.status_code == 200:
            messagebox.showinfo("Başarılı", "Dosya ESP32'ye yüklendi.")
        else:
            messagebox.showerror("Hata", "ESP32'ye yükleme başarısız oldu.")
    except Exception as e:
        messagebox.showerror("Hata", f"Bir hata oluştu: {e}")

def dosya_yukle_listeye():
    """Yerel dosyayı okuyarak listeye yükle"""
    global personel_listesi
    if os.path.exists(LOCAL_FILE_PATH):
        with open(LOCAL_FILE_PATH, "r") as f:
            lines = f.readlines()
        personel_listesi = [line.strip().split(",") for line in lines if line.strip()]
        if personel_listesi and personel_listesi[0] == ["ID", "Ad Soyad", "Dogum Tarihi"]:
            personel_listesi.pop(0)  # Başlık satırını kaldır
        liste_guncelle()
        print("Personeller dosyası listelendi.")
    else:
        print("Personeller.txt bulunamadı, liste boş.")

def formatla_iki_hane(sayi):
    """Girilen sayıyı iki haneli formata dönüştür"""
    return f"{int(sayi):02}"

def ekle():
    """Listeye yeni personel ekle"""
    personel_id = id_entry.get()
    isim = isim_entry.get()
    gun = gun_var.get()
    ay = ay_var.get()

    if not (personel_id and isim and gun and ay):
        messagebox.showwarning("Uyarı", "Tüm alanları doldurmanız gerekiyor.")
        return

    try:
        gun = formatla_iki_hane(gun)
        ay = formatla_iki_hane(ay)
    except ValueError:
        messagebox.showerror("Hata", "Gün ve Ay sadece sayı olmalıdır.")
        return

    dogum_tarihi = f"{gun}.{ay}"
    personel_listesi.append([personel_id, isim, dogum_tarihi])
    liste_guncelle()
    dosya_kaydet()  # Ekleme sonrası dosyayı otomatik kaydet
    dosya_yukle()   # Dosyayı ESP32'ye otomatik gönder
    ana_ekran_personel_listesi_guncelle()  # Ana ekrandaki personel listesini güncelle

def sil():
    """Seçilen personeli listeden sil"""
    secili = liste.curselection()
    if not secili:
        messagebox.showwarning("Uyarı", "Silmek için bir personel seçin.")
        return
    personel_listesi.pop(secili[0])
    liste_guncelle()
    dosya_kaydet()  # Silme sonrası dosyayı otomatik kaydet
    dosya_yukle()   # Dosyayı ESP32'ye otomatik gönder
    ana_ekran_personel_listesi_guncelle()  # Ana ekrandaki personel listesini güncelle

def liste_guncelle():
    """Liste kutusunu güncelle"""
    liste.delete(0, tk.END)
    for personel in personel_listesi:
        liste.insert(tk.END, f"{personel[0]}, {personel[1]}, {personel[2]}")

def sadece_rakam_girisi(entry_text, max_length):
    """Yalnızca rakam girişini sınırla ve maksimum uzunluğu kontrol et"""
    return entry_text.isdigit() and len(entry_text) <= max_length

def placeholder_girisi(entry, varsayilan):
    """Giriş alanı için placeholder kontrolü"""
    if entry.get() == "":
        entry.insert(0, varsayilan)
        entry.config(fg="gray")
    elif entry.get() == varsayilan:
        entry.delete(0, tk.END)
        entry.config(fg="black")

def personel_ekle_penceresi():
    """Personel ekleme penceresi oluştur ve modal olarak aç"""
    personel_penceresi = tk.Toplevel(root)
    personel_penceresi.title("Personel Ekle")
    personel_penceresi.transient(root)  # Ana ekranın arkasında kalmasını engeller
    personel_penceresi.grab_set()  # Kullanıcı etkileşimini bu pencereyle sınırlar

    frame = tk.Frame(personel_penceresi)
    frame.pack(padx=10, pady=10)

    # Giriş alanları
    tk.Label(frame, text="ID:").grid(row=0, column=0)
    global id_entry
    id_entry = tk.Entry(frame)
    id_entry.grid(row=0, column=1)
    id_entry.insert(0, "Örn: 74D483CE")
    id_entry.bind("<FocusIn>", lambda e: placeholder_girisi(id_entry, "Örn: 74D483CE"))

    tk.Label(frame, text="İsim:").grid(row=1, column=0)
    global isim_entry
    isim_entry = tk.Entry(frame)
    isim_entry.grid(row=1, column=1)
    isim_entry.insert(0, "Örn: Mehmet Akif Günhan")
    isim_entry.bind("<FocusIn>", lambda e: placeholder_girisi(isim_entry, "Örn: Mehmet Akif Günhan"))

    # Gün ve Ay yan yana giriş alanı
    tk.Label(frame, text="Doğum Tarihi:").grid(row=2, column=0)

    global gun_var
    gun_var = tk.StringVar()
    gun_entry = tk.Entry(frame, textvariable=gun_var, width=3, justify="center")
    gun_entry.grid(row=2, column=1, sticky="w")
    gun_entry.insert(0, "GG")  # Placeholder
    gun_entry.bind("<FocusIn>", lambda e: placeholder_girisi(gun_entry, "GG"))

    tk.Label(frame, text=".").grid(row=2, column=2)

    global ay_var
    ay_var = tk.StringVar()
    ay_entry = tk.Entry(frame, textvariable=ay_var, width=3, justify="center")
    ay_entry.grid(row=2, column=3, sticky="w")
    ay_entry.insert(0, "AA")  # Placeholder
    ay_entry.bind("<FocusIn>", lambda e: placeholder_girisi(ay_entry, "AA"))

    # Ekle ve Sil butonları
    ekle_buton = tk.Button(frame, text="Ekle", command=ekle)
    ekle_buton.grid(row=3, column=0, pady=5)

    sil_buton = tk.Button(frame, text="Sil", command=sil)
    sil_buton.grid(row=3, column=1, pady=5)

    # Liste kutusu
    global liste
    liste = tk.Listbox(personel_penceresi, width=50)
    liste.pack(padx=10, pady=10)

    dosya_kontrol_et()
    dosya_yukle_listeye()

    personel_penceresi.wait_window(personel_penceresi)  # Pencere kapanana kadar bekler

def ana_ekran_personel_listesi_guncelle():
    """Ana ekrandaki personel listesini güncelle"""
    global veri2
    personnel_listbox.delete(0, tk.END)
    veri2 = load_veri2()  # veri2 değişkenini güncelle
    for card_id, name in veri2.items():
        personnel_listbox.insert(tk.END, name)

def update_progress_bar(q, progress_bar, root):
    try:
        result = q.get_nowait()
        if result == "success":
            progress_bar["value"] = 100
            root.destroy()
        elif "error" in result:
            messagebox.showerror("Hata", f"Dosya indirilemedi: {result}")
            root.destroy()
    except Exception as e:
        print(f"Progress bar update error: {e}")
        root.after(100, update_progress_bar, q, progress_bar, root)

def create_daily_table(window, date, records, max_name_length, veri2):
    for widget in window.winfo_children():
        if isinstance(widget, ttk.LabelFrame):
            widget.destroy()

    frame = ttk.LabelFrame(window, text=f'Tarih: {date}', padding=(10, 5))
    frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=10, columnspan=2)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    columns = ('İsim', 'Girişler', 'Çıkışlar', 'Çalışma Süresi', 'Mesai Süresi', 'Mesai Kazancı')

    table = ttk.Treeview(frame, columns=columns, show='headings', height=15)
    for col in columns:
        table.heading(col, text=col, anchor='center')
        width = max_name_length * 12 if col == "İsim" else 150
        table.column(col, width=width, anchor='center')
    table.grid(row=0, column=0, sticky='nsew')

    scrollbar_vertical = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
    table.configure(yscrollcommand=scrollbar_vertical.set)
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')

    scrollbar_horizontal = ttk.Scrollbar(frame, orient='horizontal', command=table.xview)
    table.configure(xscrollcommand=scrollbar_horizontal.set)
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')

    style = ttk.Style()
    style.configure('Treeview', font=("Arial", 12), rowheight=60)
    style.configure('Treeview.Heading', font=("Arial", 12, "bold"))
    style.map('Treeview', background=[('selected', '#4caf50')])

    table.tag_configure('odd', background='#F0F0F0')
    table.tag_configure('even', background='#FFFFFF')
    table.tag_configure('absent', background='#FFCCCC')

    if not records:
        label = ttk.Label(frame, text='VERİ YOK', font=("Arial", 14, "bold"), foreground="red")
        label.grid(row=0, column=0, padx=10, pady=20)
    else:
        employees_present = set(record[0] for record in records)
        for i, record in enumerate(records):
            girisler = record[1].replace("↵", "\n")
            cikislar = record[2].replace("↵", "\n")

            giris_list = record[1].split("↵")
            cikis_list = record[2].split("↵") if record[2] else []
            
            while len(cikis_list) < len(giris_list):
                cikis_list.append("Çıkış Yok")
            
            cikislar = "\n".join(cikis_list)

            if "Çıkış Yok" in cikis_list:
                calisma_suresi = "?"
                mesai_suresi = "?"
                mesai_kazanci = "?"
            else:
                calisma_suresi = record[3]
                mesai_suresi = record[4]
                mesai_kazanci = record[5]

            tag = 'odd' if i % 2 == 0 else 'even'
            table.insert('', 'end', values=[record[0], girisler, cikislar, calisma_suresi, mesai_suresi, mesai_kazanci], tags=(tag,))

        for card_id, name in veri2.items():
            if name not in employees_present:
                table.insert('', 'end', values=[name, "-", "-", "-", "-", "-"], tags=('absent',))

    download_button = ttk.Button(frame, text='📥 Excel Olarak İndir', command=lambda: download_excel(date, records))
    download_button.grid(row=2, column=0, pady=10)

    return_to_main_button = ttk.Button(frame, text="Ana Sayfaya Dön", command=return_to_main_screen)
    return_to_main_button.grid(row=2, column=1, pady=10)

    # Instead of launching a subprocess for edit mode, call the dedicated function that embeds EditPanel inline:
    edit_button = ttk.Button(frame, text="🛠️ Düzenleme Modu Aç", command=duzenleme_modunu_ac)
    edit_button.grid(row=2, column=2, pady=10, padx=5)

def mark_islem_gunleri(cal, islem_olan_gunler):
    for date in islem_olan_gunler:
        try:
            year, month, day = map(int, date.split('-'))
            cal.calevent_create(datetime(year, month, day), 'İşlem Günü', tags='islem_gunu')
        except ValueError:
            print(f"Geçersiz tarih formatı: {date}")
    cal.tag_config('islem_gunu', background='lightblue')

def get_max_name_length(veri2):
    return max((len(name) for name in veri2.values()), default=10)

def create_monthly_table(window, month, records, max_name_length, name):
    for widget in window.winfo_children():
        if isinstance(widget, ttk.LabelFrame):
            widget.destroy()

    frame = ttk.LabelFrame(window, text=f'{month} - {name}', padding=(10, 5))
    frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=10, columnspan=2)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    columns = ('Tarih', 'Girişler', 'Çıkışlar', 'Çalışma Süresi', 'Mesai Süresi', 'Mesai Kazancı')

    table = ttk.Treeview(frame, columns=columns, show='headings', height=15)
    for col in columns:
        table.heading(col, text=col, anchor='center')
        width = max_name_length * 12 if col == "Tarih" else 150
        table.column(col, width=width, anchor='center')
    table.grid(row=0, column=0, sticky='nsew')

    scrollbar_vertical = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
    table.configure(yscrollcommand=scrollbar_vertical.set)
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')

    scrollbar_horizontal = ttk.Scrollbar(frame, orient='horizontal', command=table.xview)
    table.configure(xscrollcommand=scrollbar_horizontal.set)
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')

    style = ttk.Style()
    style.configure('Treeview', font=("Arial", 12), rowheight=60)
    style.configure('Treeview.Heading', font=("Arial", 12, "bold"))
    style.map('Treeview', background=[('selected', '#4caf50')])

    table.tag_configure('odd', background='#F0F0F0')
    table.tag_configure('even', background='#FFFFFF')
    table.tag_configure('no_data', background='#FFCCCC')

    year, month_num = map(int, month.split('-'))
    first_day = datetime(year, month_num, 1)
    last_day = min(datetime.now() - timedelta(days=1), datetime(year, month_num + 1, 1) - timedelta(days=1))
    current_day = first_day

    while current_day <= last_day:
        date_str = current_day.strftime('%Y-%m-%d')

        if date_str in records:
            record = records[date_str]

            giris_list = record[0].split("↵")
            cikis_list = record[1].split("↵") if record[1] else []

            while len(cikis_list) < len(giris_list):
                cikis_list.append("Çıkış Yok")

            cikislar = "\n".join(cikis_list)
            girisler = record[0].replace("↵", "\n")

            if "Çıkış Yok" in cikis_list:
                calisma_suresi = "?"
                mesai_suresi = "?"
                mesai_kazanci = "?"
            else:
                calisma_suresi = record[2]
                mesai_suresi = record[3]
                mesai_kazanci = record[4]

            tag = 'odd' if current_day.day % 2 == 0 else 'even'
            table.insert('', 'end', values=[date_str, girisler, cikislar, calisma_suresi, mesai_suresi, mesai_kazanci], tags=(tag,))
        else:
            table.insert('', 'end', values=[date_str, "-", "-", "-", "-", "-"], tags=('no_data',))

        current_day += timedelta(days=1)

    download_button = ttk.Button(frame, text='📥 Excel Olarak İndir', command=lambda: download_excel(month, records, name))
    download_button.grid(row=2, column=0, pady=10)

    return_to_main_button = ttk.Button(frame, text="Ana Sayfaya Dön", command=return_to_main_screen)
    return_to_main_button.grid(row=2, column=1, pady=10)


def download_excel(date, records, name=None):
    try:
        files = [('Excel Files', '*.xlsx'), ('All Files', '*.*')]
        default_filename = f"{date}_kayitlari_{name if name else ''}.xlsx".strip('_')
        file_path = asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=files,
            title="Excel Dosyasını Kaydet"
        )
        if not file_path:
            return

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = date
        sheet.append(['Tarih', 'İsim', 'Giriş Zamanı', 'Çıkış Zamanı', 'Çalışma Süresi', 'Mesai Süresi', 'Mesai Kazancı'])

        for record in records:
            if len(record) == 6:
                sheet.append([date] + record)
            else:
                print(f"Geçersiz kayıt atlandı: {record}")

        workbook.save(file_path)
        messagebox.showinfo("Başarılı", f"Dosya başarıyla kaydedildi:\n{file_path}")
    except Exception as e:
        print(f"Excel dosyası oluşturulurken bir hata oluştu: {e}")
        messagebox.showerror("Hata", f"Excel dosyası oluşturulurken bir hata oluştu: {e}")

def adjust_personnel_listbox(personnel_listbox, personnel_count):
    max_height = 30
    height = min(personnel_count, max_height)
    personnel_listbox.config(height=height)

def show_monthly_table(card_id, name):
    def on_month_selected(year, month):
        monthly_records = {}
        for date, records in data.items():
            if date.startswith(f"{year}-{month:02d}") and any(r[0] == name for r in records):
                for record in records:
                    if record[0] == name:
                        monthly_records[date] = record[1:]
        create_monthly_table(main_frame, f"{year}-{month:02d}", monthly_records, max_name_length, name)

    def on_back_clicked():
        for widget in main_frame.winfo_children():
            widget.grid()

    for widget in main_frame.winfo_children():
        widget.grid_remove()

    year = datetime.now().year
    frame = ttk.LabelFrame(main_frame, text=f"{name} için Aylık Tablolar", padding=(10, 5))
    frame.grid(row=0, column=0, sticky='ew', padx=10, pady=5, columnspan=2)

    year_label = ttk.Label(frame, text="Yıl:")
    year_label.grid(row=0, column=0, padx=5, pady=5)

    year_spinbox = ttk.Spinbox(frame, from_=2020, to=2100, width=5)
    year_spinbox.set(year)
    year_spinbox.grid(row=0, column=1, padx=5, pady=5)

    for i, month in enumerate(["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]):
        button = ttk.Button(frame, text=month,
                            command=lambda m=i+1: on_month_selected(int(year_spinbox.get()), m))
        button.grid(row=i // 6 + 1, column=i % 6, padx=5, pady=5)

    back_button = ttk.Button(frame, text="Geri Dön", command=on_back_clicked)
    back_button.grid(row=3, column=2, padx=5, pady=5)

def return_to_main_screen():
    for widget in main_frame.winfo_children():
        widget.grid()
    for widget in main_frame.winfo_children():
        if not isinstance(widget, Calendar) and not isinstance(widget, ttk.Frame):
            widget.grid_remove()

def mesai_ucreti_tanimla_penceresi():
    """Mesai ücreti tanımlama penceresi oluştur ve modal olarak aç"""
    mesai_penceresi = tk.Toplevel(root)
    mesai_penceresi.title("Mesai Ücreti Tanımla")
    mesai_penceresi.transient(root)  # Ana ekranın arkasında kalmasını engeller
    mesai_penceresi.grab_set()  # Kullanıcı etkileşimini bu pencereyle sınırlar

    frame = tk.Frame(mesai_penceresi)
    frame.pack(padx=10, pady=10)

    # Başlıklar
    tk.Label(frame, text="İsim").grid(row=0, column=0, padx=5, pady=5)
    tk.Label(frame, text="Mesai Ücreti (TL)").grid(row=0, column=1, padx=5, pady=5)

    # Giriş alanları
    entries = {}
    for i, (card_id, name) in enumerate(veri2.items(), start=1):
        tk.Label(frame, text=name).grid(row=i, column=0, padx=5, pady=5)
        ucret_var = tk.StringVar(value=str(mesai_ucretleri.get(name, 0)))
        entry = tk.Entry(frame, textvariable=ucret_var, width=10, justify="center")
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries[name] = entry

    def kaydet():
        global mesai_ucretleri, data

        for name, entry in entries.items():
            try:
                ucret = float(entry.get())
            except ValueError:
                ucret = 0
            mesai_ucretleri[name] = ucret
        
        with open('kayıtlar/mesai_ucret.txt', 'w', encoding='utf-8') as f:
            f.write('isim,mesai_ücreti\n')
            for name, ucret in mesai_ucretleri.items():
                f.write(f"{name},{ucret}\n")
        
        messagebox.showinfo("Başarılı", "Mesai ücretleri başarıyla kaydedildi.")
        
        # 1. Mesai ücretleri yeniden yükleniyor
        mesai_ucretleri = load_mesai_ucret()

        # 2. Veriler yeniden işleniyor
        data, islem_olan_gunler = process_data()

        # 3. Seçili tarihi takvimden alıp tabloyu güncelle
        secilen_tarih = cal.get_date()
        create_daily_table(main_frame, secilen_tarih, data.get(secilen_tarih, []), max_name_length, veri2)

        mesai_penceresi.destroy()

    def iptal():
        mesai_penceresi.destroy()

    # Kaydet ve İptal butonları
    kaydet_buton = tk.Button(frame, text="✅ Kaydet", command=kaydet)
    kaydet_buton.grid(row=len(veri2)+1, column=0, pady=10)

    iptal_buton = tk.Button(frame, text="❌ İptal", command=iptal)
    iptal_buton.grid(row=len(veri2)+1, column=1, pady=10)

    mesai_penceresi.wait_window(mesai_penceresi)  # Pencere kapanana kadar bekler

# -------------------------------------------------------
# New Edit Mode integration: embed EditPanel directly in gui.py
# -------------------------------------------------------
def duzenleme_modunu_ac():
    secilen_tarih = cal.get_date()

    # Remove current content in the main frame to show EditPanel
    for widget in main_frame.winfo_children():
        widget.destroy()

    # Create and add the EditPanel to the main_frame
    edit_panel = EditPanel(
        main_frame,
        secili_tarih=secilen_tarih,
        on_close=lambda: yeniden_tablo_olustur(secilen_tarih)
    )
    edit_panel.grid(row=0, column=0, sticky="nsew")

def yeniden_tablo_olustur(tarih):
    global data, islem_olan_gunler, cal

    # main_frame içeriğini temizle
    for widget in main_frame.winfo_children():
        widget.destroy()

    # Takvimi yeniden oluştur ve yerleştir
    cal = Calendar(main_frame, selectmode='day', locale='tr_TR', firstweekday='monday', date_pattern='yyyy-MM-dd')
    cal.grid(row=0, column=0, padx=10, pady=5, sticky='nw')

    # Takvime tıklanınca tabloyu yeniden oluştur
    cal.bind("<<CalendarSelected>>", lambda event: create_daily_table(
        main_frame, cal.get_date(), data.get(cal.get_date(), []), max_name_length, veri2))

    # Verileri yeniden işle
    data, islem_olan_gunler = process_data()
    mark_islem_gunleri(cal, islem_olan_gunler)  # işlem günlerini tekrar boya

    # İşlem yapılan günleri yeniden işaretle
    mark_islem_gunleri(cal, islem_olan_gunler)

    # Seçili tarih için tabloyu oluştur
    create_daily_table(main_frame, tarih, data.get(tarih, []), max_name_length, veri2)


# -------------------------------------------------------
# Main function to set up and run the application
# -------------------------------------------------------
def main(ESP32_IP, DOSYA_LISTESI_URL, DOSYA_ICERIK_URL):
    global main_frame, cal, data, max_name_length, veri2, root, personnel_listbox, mesai_ucretleri

    # İlk aşamada verileri güncelleyen pencere
    progress_root = tk.Tk()
    progress_root.title("Veri Yükleniyor...")
    progress_root.resizable(False, False)
    progress_bar = ttk.Progressbar(progress_root, orient="horizontal", length=200, mode="determinate")
    progress_bar.pack(pady=20, padx=20)
    q = queue.Queue()
    thread = threading.Thread(target=eksik_verileri_guncelle, args=(q, ESP32_IP, DOSYA_LISTESI_URL, DOSYA_ICERIK_URL))
    thread.start()
    update_progress_bar(q, progress_bar, progress_root)
    progress_root.mainloop()

    # Ana pencere
    root = tk.Tk()
    root.title('Personel Takip Sistemi')
    root.geometry('1000x700')

    root.grid_rowconfigure(0, weight=0)
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    header_frame = ttk.Frame(root)
    header_frame.grid(row=0, column=0, sticky='ew')
    ttk.Label(header_frame, text='Personel Takip Sistemi', font=('Arial', 16, 'bold')).pack(pady=10)

    content_frame = ttk.Frame(root)
    content_frame.grid(row=1, column=0, sticky='nsew')
    content_frame.columnconfigure(0, weight=1)
    content_frame.columnconfigure(1, weight=0)
    content_frame.rowconfigure(0, weight=1)

    main_frame = ttk.Frame(content_frame)
    main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
    main_frame.columnconfigure(0, weight=1)
    main_frame.grid_rowconfigure(0, weight=0)
    main_frame.grid_rowconfigure(1, weight=1)

    locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
    cal = Calendar(main_frame, selectmode='day', locale='tr_TR', firstweekday='monday', date_pattern='yyyy-MM-dd')
    cal.grid(row=0, column=0, padx=10, pady=5, sticky='nw')

    veri2 = load_veri2()
    mesai_ucretleri = load_mesai_ucret()
    max_name_length = get_max_name_length(veri2)
    data, islem_olan_gunler = process_data()
    mark_islem_gunleri(cal, islem_olan_gunler)

    today = datetime.now()
    previous_day = today - timedelta(days=1)
    previous_date = previous_day.strftime('%Y-%m-%d')
    if previous_date in data:
        create_daily_table(main_frame, previous_date, data[previous_date], max_name_length, veri2)
    else:
        create_daily_table(main_frame, today.strftime('%Y-%m-%d'), data.get(today.strftime('%Y-%m-%d'), []), max_name_length, veri2)

    cal.bind("<<CalendarSelected>>", lambda event: create_daily_table(main_frame, cal.get_date(), data.get(cal.get_date(), []), max_name_length, veri2))

    personnel_frame = ttk.Frame(content_frame)
    personnel_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
    personnel_frame.columnconfigure(0, weight=1)
    personnel_frame.rowconfigure(0, weight=1)

    personnel_listbox = tk.Listbox(personnel_frame, width=30)
    personnel_listbox.grid(row=0, column=0, sticky='nsew')
    scrollbar_listbox = ttk.Scrollbar(personnel_frame, orient='vertical', command=personnel_listbox.yview)
    personnel_listbox.configure(yscrollcommand=scrollbar_listbox.set)
    scrollbar_listbox.grid(row=0, column=1, sticky='ns')

    for card_id, name in veri2.items():
        personnel_listbox.insert(tk.END, name)

    adjust_personnel_listbox(personnel_listbox, len(veri2))
    personnel_listbox.bind("<Double-1>", lambda event: on_personnel_double_click())

    # Personel ekleme butonu
    personel_ekle_buton = tk.Button(personnel_frame, text="Personel Ekle", command=personel_ekle_penceresi)
    personel_ekle_buton.grid(row=1, column=0, pady=10)

    # Mesai ücreti tanımlama butonu
    mesai_ucreti_tanimla_buton = tk.Button(personnel_frame, text="Mesai Ücreti Tanımla", command=mesai_ucreti_tanimla_penceresi)
    mesai_ucreti_tanimla_buton.grid(row=2, column=0, pady=10)

    root.mainloop()

def on_personnel_double_click():
    try:
        selected_index = personnel_listbox.curselection()[0]
        card_id = list(veri2.keys())[selected_index]
        name = veri2[card_id]
        show_monthly_table(card_id, name)
    except IndexError:
        print("Hiçbir personel seçilmedi.")