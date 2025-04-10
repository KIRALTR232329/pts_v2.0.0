import os
import datetime
import tkinter as tk
from tkinter import messagebox
from utils import load_veri2, VERI1_PATH, VERI2_PATH


class EditPanel(tk.Frame):
    def __init__(self, parent, secili_tarih=None, on_close=None):
        super().__init__(parent)
        self.parent = parent
        self.secili_tarih = secili_tarih
        self.on_close = on_close

        self.entry_widgets = {}  # key: (kart_id, tarih), value: list of (entry saatler)
        self.duzenleme_modu = True
        self.DUZENLENMIS_YOKLAMA_PATH = os.path.join("kayıtlar", "duzenlenmis_yoklama.txt")

        self.kisiler = self.oku_kisiler()
        self.yoklamalar = self.birlestirilmis_yoklama()
        self.tarih_listesi = sorted(list(self.yoklamalar.keys()))

        # Initialize UI
        self.init_ui()

    def oku_kisiler(self):
        return load_veri2()

    def oku_yoklama(self, dosya_adi):
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

    def birlestirilmis_yoklama(self):
        yoklamalar = self.oku_yoklama(VERI1_PATH)
        duzenlemeler = self.oku_yoklama(self.DUZENLENMIS_YOKLAMA_PATH)
        for tarih, kisi_dict in duzenlemeler.items():
            if tarih not in yoklamalar:
                yoklamalar[tarih] = {}
            for kart_id, zamanlar in kisi_dict.items():
                yoklamalar[tarih][kart_id] = zamanlar
        return yoklamalar

    def saat_ciftlerine_ayir(self, saat_listesi):
        saat_listesi.sort()
        ciftler = []
        for i in range(0, len(saat_listesi), 2):
            giris = saat_listesi[i]
            cikis = saat_listesi[i + 1] if i + 1 < len(saat_listesi) else None
            ciftler.append((giris, cikis))
        return ciftler

    def tabloyu_guncelle(self):
        for widget in self.frame_tablo.winfo_children():
            widget.destroy()
        self.entry_widgets.clear()

        tarih = self.mevcut_tarih.get()
        self.lbl_tarih.config(text=f"Tarih: {tarih}" + (" (Düzenleme Açık)" if self.duzenleme_modu else ""))
        bugun_kayitlar = self.yoklamalar.get(tarih, {})

        row = 0
        for index, (kart_id, isim) in enumerate(self.kisiler.items()):
            saatler = bugun_kayitlar.get(kart_id, [])
            if not saatler:
                bg_color = "#ffcccc"
                self.entry_widgets[(kart_id, tarih)] = []

                tk.Label(self.frame_tablo, text=isim, anchor="w", font=("Arial", 11, "bold"), bg=bg_color).grid(row=row, column=0, sticky="nsew", padx=4, pady=2)

                g_entry = tk.Entry(self.frame_tablo, width=10)
                g_entry.grid(row=row, column=1, sticky="nsew", padx=2)
                self.entry_widgets[(kart_id, tarih)].append(g_entry)

                c_entry = tk.Entry(self.frame_tablo, width=10)
                c_entry.grid(row=row, column=2, sticky="nsew", padx=2)
                self.entry_widgets[(kart_id, tarih)].append(c_entry)

                tk.Label(self.frame_tablo, text="-", bg=bg_color).grid(row=row, column=3, sticky="nsew", padx=2)
                row += 1
            else:
                ciftler = self.saat_ciftlerine_ayir(saatler)
                bg_color = "#ffffff" if index % 2 == 0 else "#f2f2f2"
                entry_list = []
                for i, (g, c) in enumerate(ciftler):
                    if self.duzenleme_modu:
                        g_entry = tk.Entry(self.frame_tablo, width=10)
                        g_entry.insert(0, g.strftime("%H:%M:%S"))
                        g_entry.grid(row=row, column=1, sticky="nsew", padx=2)

                        c_entry = tk.Entry(self.frame_tablo, width=10)
                        if c:
                            c_entry.insert(0, c.strftime("%H:%M:%S"))
                        c_entry.grid(row=row, column=2, sticky="nsew", padx=2)

                        sure = str(c - g) if c else "-"
                        tk.Label(self.frame_tablo, text=sure, bg=bg_color).grid(row=row, column=3, sticky="nsew", padx=2)

                        entry_list.extend([g_entry, c_entry])
                    else:
                        giris = g.strftime("%H:%M:%S")
                        cikis = c.strftime("%H:%M:%S") if c else "-"
                        sure = str(c - g) if c else "-"
                        tk.Label(self.frame_tablo, text=giris, bg=bg_color).grid(row=row, column=1, sticky="nsew", padx=2)
                        tk.Label(self.frame_tablo, text=cikis, bg=bg_color).grid(row=row, column=2, sticky="nsew", padx=2)
                        tk.Label(self.frame_tablo, text=sure, bg=bg_color).grid(row=row, column=3, sticky="nsew", padx=2)
                    row += 1

                tk.Label(self.frame_tablo, text=isim, anchor="w", font=("Arial", 11, "bold"), bg=bg_color).grid(row=row - len(ciftler), column=0, rowspan=len(ciftler), sticky="nsew", padx=4, pady=2)
                if self.duzenleme_modu:
                    self.entry_widgets[(kart_id, tarih)] = entry_list

    def kaydet_duzenlemeler(self):
        degisenler = 0
        for (kart_id, tarih), entry_list in self.entry_widgets.items():
            yeni_saatler = []
            for e in entry_list:
                saat = e.get().strip()
                if saat:
                    try:
                        datetime.datetime.strptime(saat, "%H:%M:%S")
                        yeni_saatler.append(saat)
                    except:
                        messagebox.showerror("Hatalı Saat", f"{self.kisiler.get(kart_id, 'Bilinmeyen Kişi')} - {tarih} içinde geçersiz saat formatı: {saat}")
                        return

            eski_saatler = [z.strftime("%H:%M:%S") for z in self.yoklamalar.get(tarih, {}).get(kart_id, [])]
            if yeni_saatler != eski_saatler:
                degisenler += 1
                satirlar = []
                if os.path.exists(self.DUZENLENMIS_YOKLAMA_PATH):
                    with open(self.DUZENLENMIS_YOKLAMA_PATH, "r", encoding="utf-8") as f:
                        satirlar = f.readlines()

                yeni_satirlar = []
                for satir in satirlar:
                    try:
                        kid, zaman_str = satir.strip().split(",")
                        zaman = datetime.datetime.strptime(zaman_str, "%Y-%m-%d %H:%M:%S")
                        if not (kid == kart_id and zaman.date().isoformat() == tarih):
                            yeni_satirlar.append(satir)
                    except:
                        yeni_satirlar.append(satir)

                for s in yeni_saatler:
                    yeni_satirlar.append(f"{kart_id},{tarih} {s}\n")

                with open(self.DUZENLENMIS_YOKLAMA_PATH, "w", encoding="utf-8") as f:
                    f.writelines(yeni_satirlar)

        if degisenler:
            self.yoklamalar = self.birlestirilmis_yoklama()

        if self.on_close:
            self.on_close()

    def iptal_et(self):
        if self.on_close:
            self.on_close()
        self.destroy()

    def ileri_tarih(self):
        indeks = self.tarih_listesi.index(self.mevcut_tarih.get())
        if indeks < len(self.tarih_listesi) - 1:
            self.mevcut_tarih.set(self.tarih_listesi[indeks + 1])
            self.tabloyu_guncelle()

    def geri_tarih(self):
        indeks = self.tarih_listesi.index(self.mevcut_tarih.get())
        if indeks > 0:
            self.mevcut_tarih.set(self.tarih_listesi[indeks - 1])
            self.tabloyu_guncelle()

    def init_ui(self):
        if self.secili_tarih and self.secili_tarih in self.tarih_listesi:
            self.mevcut_tarih = tk.StringVar(value=self.secili_tarih)
        else:
            self.mevcut_tarih = tk.StringVar(value=self.tarih_listesi[0] if self.tarih_listesi else "")

        frame_ust = tk.Frame(self, bg="#d0d0d0")
        frame_ust.pack(fill="x")
        btn_ana_ekran = tk.Button(frame_ust, text="Ana Ekrana Dön", command=self.iptal_et)
        btn_ana_ekran.pack(side="right", padx=10, pady=5)

        self.lbl_tarih = tk.Label(self, text="", font=("Arial", 14))
        self.lbl_tarih.pack(pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack()
        btn_kaydet = tk.Button(btn_frame, text="💾 Kaydet Değişiklikler", command=self.kaydet_duzenlemeler)
        btn_kaydet.pack(side="left", padx=10)
        btn_iptal = tk.Button(btn_frame, text="❌ İptal Et", command=self.iptal_et)
        btn_iptal.pack(side="left", padx=10)

        tk.Button(btn_frame, text="◀ Geri", command=self.geri_tarih, width=10).pack(side="left", padx=10)
        tk.Button(btn_frame, text="İleri ▶", command=self.ileri_tarih, width=10).pack(side="left", padx=10)

        frame_baslik = tk.Frame(self, bg="#d0d0d0")
        frame_baslik.pack(fill="x")
        basliklar = ["İsim", "Giriş Saatleri", "Çıkış Saatleri", "Süreler"]
        for i, b in enumerate(basliklar):
            tk.Label(frame_baslik, text=b, font=("Arial", 12, "bold"), bg="#d0d0d0", padx=8, pady=6).grid(row=0, column=i, sticky="nsew")

        canvas = tk.Canvas(self)
        self.scroll_y = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=self.scroll_y.set)
        self.scroll_y.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self.frame_tablo = tk.Frame(canvas)
        canvas.create_window((0, 0), window=self.frame_tablo, anchor="nw", tags="tablo")
        self.frame_tablo.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.tabloyu_guncelle()