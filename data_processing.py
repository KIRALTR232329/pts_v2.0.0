import os
import requests
from datetime import datetime, timedelta
from utils import load_veri2, load_mesai_ucret, VERI1_PATH, birlestirilmis_yoklama_verisi
from esp32 import ensure_valid_esp32_ip

def son_guncellenen_tarih():
    if not os.path.exists(VERI1_PATH):
        return None
    with open(VERI1_PATH, "r", encoding="utf-8", errors='replace') as f:
        satirlar = f.readlines()
    tarihler = sorted(set(satir.split(",")[1][:10] for satir in satirlar if "," in satir))
    return tarihler[-1] if tarihler else None

def eksik_dosyalari_bul(ESP32_IP, DOSYA_LISTESI_URL):
    try:
        yanit = requests.get(DOSYA_LISTESI_URL)
        yanit.raise_for_status()
        dosya_listesi = yanit.json()
    except Exception as e:
        print(f"⚠ Dosya listesi alınamadı: {e}")
        ESP32_IP = ensure_valid_esp32_ip()
        DOSYA_LISTESI_URL = f"http://{ESP32_IP}/dosya_listesi"
        return eksik_dosyalari_bul(ESP32_IP, DOSYA_LISTESI_URL)

    bugun = datetime.now().strftime("%Y-%m-%d")
    dosya_listesi = [dosya for dosya in dosya_listesi if dosya[:10] < bugun]

    son_tarih = son_guncellenen_tarih()
    if not son_tarih:
        return dosya_listesi

    return [dosya for dosya in dosya_listesi if dosya[:10] > son_tarih]

def eksik_verileri_guncelle(q, ESP32_IP, DOSYA_LISTESI_URL, DOSYA_ICERIK_URL):
    eksik_dosyalar = eksik_dosyalari_bul(ESP32_IP, DOSYA_LISTESI_URL)
    if not eksik_dosyalar:
        print("✅ Güncellenecek veri yok.")
        q.put("success")
        return

    try:
        with open(VERI1_PATH, "a", encoding="utf-8", errors='replace') as f:
            for dosya in eksik_dosyalar:
                try:
                    yanit = requests.get(DOSYA_ICERIK_URL.format(dosya))
                    yanit.raise_for_status()
                    f.write(yanit.text + "\n")
                    print(f"✅ {dosya} güncellendi.")
                except Exception as e:
                    print(f"⚠ : {e}")
        q.put("success")
    except Exception as e:
        q.put(f"error: {e}")

def process_data():
    yoklamalar = birlestirilmis_yoklama_verisi()
    veri2 = load_veri2()
    mesai_ucret = load_mesai_ucret()
    daily_records = {}
    islem_olan_gunler = set()

    for tarih, kisi_dict in yoklamalar.items():
        for kart_id, zamanlar in kisi_dict.items():
            date_str = tarih
            islem_olan_gunler.add(date_str)

            if date_str not in daily_records:
                daily_records[date_str] = {}
            if kart_id not in daily_records[date_str]:
                daily_records[date_str][kart_id] = {'girisler': [], 'cikislar': []}

            for zaman in zamanlar:
                time_str = zaman.strftime("%H:%M:%S")
                if len(daily_records[date_str][kart_id]['girisler']) == len(daily_records[date_str][kart_id]['cikislar']):
                    daily_records[date_str][kart_id]['girisler'].append(time_str)
                else:
                    daily_records[date_str][kart_id]['cikislar'].append(time_str)

    table_data = {}
    for date, records in daily_records.items():
        table_data[date] = []
        for card_id, times in records.items():
            try:
                if card_id not in veri2:
                    continue
                girisler = times['girisler']
                cikislar = times['cikislar']
                total_work_time = timedelta()

                for i in range(min(len(girisler), len(cikislar))):
                    try:
                        giris_time = datetime.strptime(girisler[i], '%H:%M:%S')
                        cikis_time = datetime.strptime(cikislar[i], '%H:%M:%S')
                        if cikis_time > giris_time:
                            work_time = cikis_time - giris_time
                            total_work_time += work_time
                    except ValueError:
                        print(f"Geçersiz zaman formatı atlandı: {girisler[i]} - {cikislar[i]}")

                mesai = total_work_time - timedelta(hours=10)
                mesai_str = f"{'+' if mesai > timedelta(0) else '-'}{str(abs(mesai))}"
                mesai_saat = mesai.total_seconds() / 3600
                mesai_kazanci = mesai_saat * mesai_ucret.get(veri2[card_id], 0)
                mesai_kazanci_str = f"{mesai_kazanci:.2f} TL"

                table_data[date].append([
                    veri2[card_id],
                    "↵".join(girisler) if girisler else "-",
                    "↵".join(cikislar) if cikislar else "-",
                    str(total_work_time),
                    mesai_str,
                    mesai_kazanci_str
                ])

            except ValueError:
                print(f"Geçersiz zaman verisi atlandı: {times}")
                continue

    return table_data, islem_olan_gunler