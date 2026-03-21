import requests
import sys

url = "https://www.dizibox.live/love-story-1-sezon-1-bolum-hd-izle"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Content Length: {len(response.text)}")
print(response.text[:1000])
