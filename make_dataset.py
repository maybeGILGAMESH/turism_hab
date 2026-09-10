import os
import requests
import urllib.parse
import zipfile
from tqdm import tqdm
from bs4 import BeautifulSoup
import time

# === Параметры ===
IMAGES_PER_PLACE = 10
OUTPUT_DIR = "dataset"
OUTPUT_ZIP = "dataset.zip"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# === Список достопримечательностей ===
places = [
    "Нарын-кала Дербент", "Джума-мечеть Дербент", "Сулакский каньон", "Бархан Сарыкум",
    "Чиркейское водохранилище", "Гамсутль аул", "Гунибское плато", "Хунзахское плато",
    "Село Кубачи", "Ахулго Дагестан", "Мечеть Сердце Чечни Грозный", "Аргунская мечеть Сердце Матери",
    "Озеро Кезеной-Ам", "Итум-Кали башни", "Цой-Педе некрополь", "Ушкалойские башни", "Вовнушки",
    "Гос. музей-заповедник Эрзи", "Храм Тхаба-Ерды", "Егикал Ингушетия", "Таргимские башни",
    "Даргавс город мертвых", "Дзивгисская крепость", "Свято-Успенский Аланский монастырь",
    "Куртатинское ущелье", "Кармадонское ущелье", "Нац парк Алания", "Эльбрус", "Приэльбрусский парк",
    "Чегемские водопады", "Голубые озера КБР", "Верхняя Балкария", "Чегемское ущелье",
    "Безенгийская стена", "Домбай", "Тебердинский заповедник", "Архыз", "Нижне-Архызские храмы",
    "Сентинский храм", "Шоанинский храм", "Пятигорск исторический центр", "Провал Пятигорск",
    "Гора Машук", "Кисловодский Курортный парк", "Дворец эмира Бухарского Железноводск",
    "Домик Лермонтова Пятигорск", "Плато Лаго-Наки", "Хаджохская теснина", "Водопады Руфабго",
    "Большой Ахун башня Сочи"
]

# === Функция для поиска изображений ===
def get_image_urls(query, max_images=10):
    search_url = f"https://www.bing.com/images/search?q={urllib.parse.quote_plus(query)}&form=HDRSC2&first=1&tsc=ImageBasicHover"
    resp = requests.get(search_url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for a in soup.find_all("a", {"class": "iusc"}):
        try:
            m = eval(a.get("m"))
            url = m["murl"]
            if url.lower().startswith("http"):
                urls.append(url)
            if len(urls) >= max_images:
                break
        except Exception:
            continue
    return urls

# === Создание датасета ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

for idx, place in enumerate(places, start=1):
    folder_name = f"{idx:02d}_{place.replace(' ', '_').replace('-', '_')}"
    folder_path = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    print(f"\n📍 {idx}. {place}")

    urls = get_image_urls(place + " фото с земли", IMAGES_PER_PLACE * 2)
    if not urls:
        print("⚠️ Не удалось найти изображения.")
        continue

    count = 0
    for url in tqdm(urls, desc=f"Скачивание {place}", total=IMAGES_PER_PLACE):
        try:
            img_data = requests.get(url, headers=HEADERS, timeout=10).content
            with open(os.path.join(folder_path, f"photo_{count + 1}.jpg"), "wb") as f:
                f.write(img_data)
            count += 1
            if count >= IMAGES_PER_PLACE:
                break
            time.sleep(0.5)
        except Exception:
            continue

print("\n✅ Все изображения скачаны. Создание архива...")

# === Архивирование ===
with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(OUTPUT_DIR):
        for file in files:
            path = os.path.join(root, file)
            zipf.write(path, arcname=os.path.relpath(path, OUTPUT_DIR))

print(f"🎉 Готово! Архив сохранён как {OUTPUT_ZIP}")
