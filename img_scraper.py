import requests
from bs4 import BeautifulSoup as bs


city = "Berlin"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

params = {
    "q": city,
    "tbh": "isch",
}

html = requests.get("https://www.google.com/search", params=params, headers=headers, timeout=30)

soup = bs(html.content, features="html.parser")

images = soup.select("img")
print(images)

images_url = images[1]['src']








