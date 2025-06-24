import requests
import urllib.parse

def fetch_price(skin_name):
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=3&market_hash_name={encoded_name}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            price_str = data.get("lowest_price", "0").replace("€", "").replace(",", ".").strip()
            return float(price_str)
        else:
            return None
    except Exception as e:
        print(f"Fehler beim Abrufen für '{skin_name}': {e}")
        return None

def fetch_price(skin_name):
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=3&market_hash_name={encoded_name}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            price_str = data.get("lowest_price", "0").replace("€", "").replace(",", ".").strip()
            volume_str = data.get("volume", "0").replace(",", "").strip()
            return float(price_str), int(volume_str)
        else:
            return None, None
    except Exception as e:
        print(f"Fehler beim Abrufen für '{skin_name}': {e}")
        return None, None
