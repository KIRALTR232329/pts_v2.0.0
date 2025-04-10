import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os

def show_splash_and_start(main_func):
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.geometry("400x400+{}+{}".format(
        (splash.winfo_screenwidth() - 400) // 2,
        (splash.winfo_screenheight() - 400) // 2
    ))
    splash.configure(bg='white')  # Arka planı beyaz yapıyoruz

    # Görev çubuğu ve uygulama simgesi ayarlama
    icon_path = os.path.join("kayıtlar", "logo.ico")
    splash.iconbitmap(icon_path)

    # Logo görselini yükle ve yuvarlak hale getir
    img_path = os.path.join("kayıtlar", "logo.png")
    logo_img = Image.open(img_path).convert("RGBA")
    logo_img = logo_img.resize((300, 300), Image.Resampling.LANCZOS)

    # Yuvarlak bir maske oluştur ve uygula
    mask = Image.new("L", logo_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, logo_img.size[0], logo_img.size[1]), fill=255)
    rounded_logo = Image.new("RGBA", logo_img.size)
    rounded_logo.paste(logo_img, (0, 0), mask)

    logo_photo = ImageTk.PhotoImage(rounded_logo)

    # Şeffaf arka plana sahip yuvarlak resmi göster
    label = tk.Label(splash, image=logo_photo, bg="white", bd=0)
    label.image = logo_photo
    label.pack(expand=True)

    # Kapanış ve ana fonksiyonu başlatma
    splash.after(2500, lambda: [splash.destroy(), main_func()])
    splash.mainloop()