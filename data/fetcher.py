import requests
import urllib.parse
import re
from typing import Tuple, Optional

# Konstanten
STEAM_API_BASE_URL = "https://steamcommunity.com/market/priceoverview/"
CSGO_APP_ID = "730"
EUR_CURRENCY_ID = "3"
REQUEST_TIMEOUT = 10

def _parse_price_string(price_str: str) -> float:
    """
    Parst einen Preis-String und konvertiert ihn zu einem Float.
    
    Args:
        price_str: Preis-String wie "1,23 €" oder "12.34"
        
    Returns:
        Float-Wert des Preises
    """
    if not price_str:
        return 0.0
    
    # Entferne alle nicht-numerischen Zeichen außer Punkt, Komma und Minus
    cleaned = re.sub(r'[^\d.,-]', '', price_str.strip())
    
    # Ersetze Komma durch Punkt für Dezimalstellen
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def _parse_volume_string(volume_str: str) -> int:
    """
    Parst einen Volume-String und konvertiert ihn zu einem Integer.
    
    Args:
        volume_str: Volume-String wie "1,234"
        
    Returns:
        Integer-Wert des Volumes
    """
    if not volume_str:
        return 0
    
    # Entferne alle nicht-numerischen Zeichen
    cleaned = re.sub(r'[^\d]', '', volume_str.strip())
    
    try:
        return int(cleaned)
    except ValueError:
        return 0

def fetch_price(skin_name: str) -> Tuple[Optional[float], Optional[int]]:
    """
    Ruft den aktuellen Marktpreis und das Handelsvolumen für einen CS:GO Skin ab.
    
    Args:
        skin_name: Name des Skins (z.B. "AK-47 | Redline (Field-Tested)")
        
    Returns:
        Tuple von (Preis, Volume) oder (None, None) bei Fehlern
    """
    if not skin_name or not skin_name.strip():
        return None, None
    
    # Parameter für die API
    params = {
        'appid': CSGO_APP_ID,
        'currency': EUR_CURRENCY_ID,
        'market_hash_name': skin_name.strip()
    }
    
    try:
        response = requests.get(
            STEAM_API_BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            print(f"Steam API Fehler für '{skin_name}': Anfrage nicht erfolgreich")
            return None, None
        
        # Preis und Volume parsen
        price = _parse_price_string(data.get("lowest_price", ""))
        volume = _parse_volume_string(data.get("volume", ""))
        
        return price, volume
        
    except requests.exceptions.RequestException as e:
        print(f"Netzwerk-Fehler beim Abrufen für '{skin_name}': {e}")
        return None, None
    except ValueError as e:
        print(f"JSON-Parse-Fehler für '{skin_name}': {e}")
        return None, None
    except Exception as e:
        print(f"Unerwarteter Fehler beim Abrufen für '{skin_name}': {e}")
        return None, None
