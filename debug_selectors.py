import requests
from bs4 import BeautifulSoup

url = "https://www.dizibox.live/love-story-1-sezon-1-bolum-hd-izle"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

selector1 = "#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-archive > span"
selector2 = "#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-episode"

print(f"Selector 1 result: {soup.select_one(selector1)}")
print(f"Selector 2 result: {soup.select_one(selector2)}")

# Also search for text patterns if selectors fail
if not soup.select_one(selector1):
    print("Selector 1 failed. Searching for h1...")
    h1 = soup.find('h1')
    if h1:
        print(f"H1 content: {h1.prettify()}")
