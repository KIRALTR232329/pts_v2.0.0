import os
import requests
from tkinter import simpledialog, messagebox
from utils import ESP32_IP_PATH

def get_esp32_ip():
    if os.path.exists(ESP32_IP_PATH):
        with open(ESP32_IP_PATH, 'r') as f:
            return f.read().strip()
    return None

def save_esp32_ip(ip):
    with open(ESP32_IP_PATH, 'w') as f:
        f.write(ip)

def test_esp32_ip(ip):
    try:
        response = requests.get(f"http://{ip}/dosya_listesi", timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False

def prompt_for_ip():
    return simpledialog.askstring("IP Adresi Girişi", "Lütfen ESP32'nin IP adresini girin:")

def ensure_valid_esp32_ip():
    ip = get_esp32_ip()
    if ip and test_esp32_ip(ip):
        return ip
    while True:
        ip = prompt_for_ip()
        if ip and test_esp32_ip(ip):
            save_esp32_ip(ip)
            return ip
        else:
            messagebox.showerror("Bağlantı Hatası", "Geçersiz IP adresi. Lütfen tekrar deneyin.")