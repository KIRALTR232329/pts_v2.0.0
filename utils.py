import os
import datetime
import csv
from tkinter import messagebox

# File paths
VERI1_PATH = 'kayıtlar/kayit.txt'
VERI2_PATH = 'kayıtlar/veri2.txt'
MASAUSTU_PATH = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Masaüstü')
ESP32_IP_PATH = 'kayıtlar/esp32_ip.txt'
MESAI_UCRET_PATH = 'kayıtlar/mesai_ucret.txt'

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def ensure_files_exist():
    ensure_directory_exists('kayıtlar')
    for path in [VERI1_PATH, VERI2_PATH, ESP32_IP_PATH, MESAI_UCRET_PATH]:
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                if path == MESAI_UCRET_PATH:
                    f.write('isim,mesai_ücreti\nMehmet Akif Günhan,60\n')

def load_csv_file(file_path, has_header=True):
    data = []
    if not os.path.exists(file_path):
        messagebox.showerror("Dosya Hatası", f"{file_path} dosyası bulunamadı.")
        return data
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            reader = csv.reader(file)
            if has_header:
                next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    data.append(row)
                else:
                    print("Hatalı veya boş satır atlandı. Lütfen veri dosyasını kontrol edin.")
    except Exception as e:
        messagebox.showerror("Veri Yükleme Hatası", str(e))
    return data

def load_veri1():
    return load_csv_file(VERI1_PATH, has_header=False)

def load_veri2():
    data = load_csv_file(VERI2_PATH, has_header=False)
    return {row[0]: row[1] for row in data}

def load_mesai_ucret():
    data = load_csv_file(MESAI_UCRET_PATH, has_header=True)
    return {row[0]: float(row[1]) for row in data}

def get_max_name_length(veri2):
    return max((len(name) for name in veri2.values()), default=10)

def oku_yoklama_dosyasi(dosya_adi):
    yoklamalar = {}
    if not os.path.exists(dosya_adi):
        return yoklamalar
    with open(dosya_adi, "r", encoding="utf-8") as f:
        for satir in f:
            try:
                kart_id, zaman_str = satir.strip().split(",")
                zaman = datetime.datetime.strptime(zaman_str, "%Y-%m-%d %H:%M:%S")
                tarih_str = zaman.date().isoformat()
                if tarih_str not in yoklamalar:
                    yoklamalar[tarih_str] = {}
                if kart_id not in yoklamalar[tarih_str]:
                    yoklamalar[tarih_str][kart_id] = []
                yoklamalar[tarih_str][kart_id].append(zaman)
            except:
                continue
    return yoklamalar

def birlestirilmis_yoklama_verisi():
    DUZENLENMIS_PATH = os.path.join("kayıtlar", "duzenlenmis_yoklama.txt")
    veri1 = oku_yoklama_dosyasi(VERI1_PATH)
    veri2 = oku_yoklama_dosyasi(DUZENLENMIS_PATH)

    # Öncelik: duzenlenmis_yoklama.txt
    for tarih, kisi_dict in veri2.items():
        if tarih not in veri1:
            veri1[tarih] = {}
        for kart_id, zamanlar in kisi_dict.items():
            veri1[tarih][kart_id] = zamanlar
    return veri1