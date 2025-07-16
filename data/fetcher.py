"""
CS Skin Tracker - Steam Community Market API Integration
=======================================================

Dieses Modul implementiert die Integration mit der Steam Community Market API
für das Abrufen von Marktdaten für Counter-Strike Skins.

Hauptfunktionen:
- fetch_comprehensive_market_data(): Umfassende Marktdaten-Abfrage
- fetch_price(): Legacy-Funktion für einfache Preis-Abfragen
- MarketData: Datenklasse für strukturierte Marktinformationen

API-Details:
- Steam Community Market API (offiziell, kostenlos)
- Rate-Limiting: Empfohlen 2+ Sekunden zwischen Requests
- Currency: Euro (ID: 3)
- App-ID: 730 (Counter-Strike Global Offensive)

Technische Features:
- Robuste String-Parsing für internationale Preisformate
- Umfassende Exception-Behandlung
- Type-Hints für bessere Code-Qualität
- Dataclass-basierte Datenstrukturen

Author: Linus
Version: 1.0
"""

import requests
import urllib.parse
import re
from typing import Tuple, Optional, Union
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════════
# API-KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Steam Community Market API Endpoints
STEAM_API_BASE_URL = "https://steamcommunity.com/market/priceoverview/"

# Steam-spezifische IDs
CSGO_APP_ID = "730"           # Counter-Strike: Global Offensive
EUR_CURRENCY_ID = "3"         # Euro Currency (1=USD, 2=GBP, 3=EUR, etc.)

# Request-Konfiguration
REQUEST_TIMEOUT = 10          # Sekunden für HTTP-Requests
USER_AGENT = "CS-Skin-Tracker/2.0 (Python-Requests)"

# Rate-Limiting Empfehlungen
RECOMMENDED_DELAY = 2.0       # Sekunden zwischen Requests (API-Schonung)
MAX_RETRIES = 3               # Anzahl Wiederholungsversuche bei Fehlern

# ═══════════════════════════════════════════════════════════════════════════════
# DATENSTRUKTUREN
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketData:
    """
    Datenstruktur für umfassende Marktdaten eines CS Skins.
    
    Diese Klasse kapselt alle verfügbaren Marktinformationen von der Steam API
    und berechnet zusätzliche Metriken wie Bid-Ask Spread.
    
    Attributes:
        lowest_price (float): Niedrigster verfügbarer Marktpreis in Euro
        median_price (float): Median-Preis der letzten Transaktionen in Euro
        volume (int): Anzahl der Transaktionen in den letzten 24h
        spread_absolute (float): Absoluter Spread (median - lowest) in Euro
        spread_percentage (float): Relativer Spread als Prozentsatz
        
    Properties:
        has_valid_data: Validierung der Datenqualität
        
    Business-Logic:
        - lowest_price: Preis für sofortigen Kauf
        - median_price: Durchschnittlicher Marktpreis
        - spread: Indikator für Marktliquidität (niedrig = liquid)
        - volume: Popularitäts- und Aktivitätsindikator
        
    Example:
        >>> data = MarketData(24.50, 25.30, 145, 0.80, 3.27)
        >>> print(f"Spread: {data.spread_percentage:.1f}%")
        Spread: 3.3%
    """
    lowest_price: float
    median_price: float
    volume: int
    spread_absolute: float      # |median_price - lowest_price|
    spread_percentage: float    # (spread_absolute / lowest_price) * 100
    
    @property
    def has_valid_data(self) -> bool:
        """
        Prüft, ob die Marktdaten gültig und verwendbar sind.
        
        Returns:
            bool: True wenn Daten valid, False bei ungültigen/fehlenden Daten
            
        Validation-Kriterien:
        - lowest_price > 0 (muss positiver Wert sein)
        - volume > 0 (mindestens eine Transaktion)
        
        Note:
            median_price kann 0 sein (bei sehr seltenen Items)
            spread-Werte können 0 sein (bei identischen Preisen)
        """
        return self.lowest_price > 0 and self.volume > 0
    
    def __str__(self) -> str:
        """String-Repräsentation für Debugging."""
        return (f"MarketData(lowest={self.lowest_price:.2f}€, "
                f"median={self.median_price:.2f}€, "
                f"volume={self.volume}, "
                f"spread={self.spread_percentage:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════════════
# STRING-PARSING-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_price_string(price_str: str) -> float:
    """
    Parst einen Preis-String von der Steam API zu einem Float-Wert.
    
    Die Steam API gibt Preise in verschiedenen Formaten zurück, abhängig von
    der Benutzersprache und Region. Diese Funktion normalisiert alle Formate.
    
    Args:
        price_str (str): Roher Preis-String von der API
        
    Returns:
        float: Numerischer Preiswert in Euro
        
    Supported Formats:
        - "1,23 €" (Deutsche Notation)
        - "5,--€" (Deutsche Notation ohne Nachkommastellen)
        - "$12.34" (US-Dollar, wird als Zahl geparst)
        - "12.34" (Reine Zahl)
        - "1 234,56 €" (Mit Tausender-Trennzeichen)
        - "" (Leerer String -> 0.0)
        
    Error-Handling:
        - Ungültige Strings returnieren 0.0
        - Logging bei unerwarteten Formaten
        
    Example:
        >>> _parse_price_string("24,50 €")
        24.5
        >>> _parse_price_string("5,--€")
        5.0
        >>> _parse_price_string("$12.34")
        12.34
        >>> _parse_price_string("invalid")
        0.0
    """
    if not price_str:
        return 0.0
    
    # ═══════════════════════════════════════════════════════════════════════
    # STRING-NORMALISIERUNG
    # ═══════════════════════════════════════════════════════════════════════
    
    # Entferne alle Zeichen außer Ziffern, Punkt, Komma und Minus
    # Regex: Behält nur numerische Zeichen und Dezimaltrennzeichen
    cleaned = re.sub(r'[^\d.,-]', '', price_str.strip())
    
    # ═══════════════════════════════════════════════════════════════════════
    # SPEZIALFALL: Deutsche ",--" Notation (z.B. "5,--€")
    # ═══════════════════════════════════════════════════════════════════════
    
    if cleaned.endswith(',--'):
        # "5,--" -> "5" (Ganzzahl ohne Nachkommastellen)
        integer_part = cleaned[:-3]  # Entferne ",--"
        if integer_part.isdigit():
            cleaned = integer_part
        else:
            # Fallback wenn vor ",--" keine reine Zahl steht
            cleaned = integer_part.replace('.', '').replace(',', '')
    
    elif cleaned.endswith('.-'):
        # "5.-" -> "5" (alternative Notation)
        integer_part = cleaned[:-2]  # Entferne ".-"
        if integer_part.isdigit():
            cleaned = integer_part
        else:
            cleaned = integer_part.replace('.', '').replace(',', '')
    
    # ═══════════════════════════════════════════════════════════════════════
    # STANDARD-DEZIMALTRENNZEICHEN-BEHANDLUNG
    # ═══════════════════════════════════════════════════════════════════════
    
    elif ',' in cleaned and '.' in cleaned:
        # Format: "1.234,56" -> "1234.56"
        # Letztes Komma ist Dezimaltrennzeichen, Punkte sind Tausender-Trenner
        parts = cleaned.split(',')
        if len(parts) == 2:
            integer_part = parts[0].replace('.', '')  # Entferne Tausender-Punkte
            decimal_part = parts[1]
            cleaned = f"{integer_part}.{decimal_part}"
    elif ',' in cleaned:
        # Format: "1234,56" -> "1234.56"
        # Komma als Dezimaltrennzeichen (Europa)
        cleaned = cleaned.replace(',', '.')
    # Punkte bleiben als Dezimaltrennzeichen (US-Format)
    
    # ═══════════════════════════════════════════════════════════════════════
    # NUMERISCHE KONVERTIERUNG
    # ═══════════════════════════════════════════════════════════════════════
    
    try:
        return float(cleaned)
    except ValueError:
        # Logging für Debugging unbekannter Formate
        print(f"Warning: Unparsbarer Preis-String nach Bereinigung: '{price_str}' -> '{cleaned}'")
        return 0.0

def _parse_volume_string(volume_str: str) -> int:
    """
    Parst einen Volume-String von der Steam API zu einem Integer-Wert.
    
    Args:
        volume_str (str): Roher Volume-String von der API
        
    Returns:
        int: Numerischer Volume-Wert
        
    Supported Formats:
        - "1,234" (Mit Tausender-Komma)
        - "1.234" (Mit Tausender-Punkt)
        - "1 234" (Mit Leerzeichen)
        - "1234" (Reine Zahl)
        - "" (Leerer String -> 0)
        
    Example:
        >>> _parse_volume_string("1,234")
        1234
        >>> _parse_volume_string("5")
        5
    """
    if not volume_str:
        return 0
    
    # Entferne alle nicht-numerischen Zeichen (Kommas, Punkte, Leerzeichen)
    cleaned = re.sub(r'[^\d]', '', volume_str.strip())
    
    try:
        return int(cleaned)
    except ValueError:
        print(f"Warning: Unparsbarer Volume-String: '{volume_str}' -> '{cleaned}'")
        return 0

# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY API-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_price(skin_name: str) -> Tuple[Optional[float], Optional[int]]:
    """
    Legacy-Funktion für einfache Preis- und Volume-Abfragen.
    
    Diese Funktion wird für Rückwärtskompatibilität beibehalten, aber
    fetch_comprehensive_market_data() sollte für neue Implementierungen
    bevorzugt werden.
    
    Args:
        skin_name (str): Vollständiger Name des Skins
        
    Returns:
        Tuple[Optional[float], Optional[int]]: (Preis, Volume) oder (None, None)
        
    Deprecated:
        Verwenden Sie fetch_comprehensive_market_data() für vollständige Daten.
        
    Example:
        >>> price, volume = fetch_price("AK-47 | Redline (Field-Tested)")
        >>> print(f"Preis: {price}€, Volume: {volume}")
        Preis: 24.5€, Volume: 142
    """
    if not skin_name or not skin_name.strip():
        return None, None
    
    # Parameter für die Steam API
    params = {
        'appid': CSGO_APP_ID,
        'currency': EUR_CURRENCY_ID,
        'market_hash_name': skin_name.strip()
    }
    
    try:
        # HTTP-Request mit Timeout
        response = requests.get(
            STEAM_API_BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': USER_AGENT}
        )
        response.raise_for_status()  # Wirft Exception bei HTTP-Fehlern
        
        # JSON-Response parsen
        data = response.json()

        # API-Success-Flag prüfen
        if not data.get("success"):
            print(f"Steam API Fehler für '{skin_name}': Anfrage nicht erfolgreich")
            return None, None
        
        # Daten extrahieren und parsen
        price = _parse_price_string(data.get("lowest_price", ""))
        volume = _parse_volume_string(data.get("volume", ""))
        
        return price, volume
        
    except requests.exceptions.Timeout:
        print(f"Timeout beim Abrufen für '{skin_name}' (>{REQUEST_TIMEOUT}s)")
        return None, None
    except requests.exceptions.ConnectionError:
        print(f"Verbindungsfehler beim Abrufen für '{skin_name}' (Netzwerk/Internet prüfen)")
        return None, None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP-Fehler beim Abrufen für '{skin_name}': {e}")
        return None, None
    except ValueError as e:
        print(f"JSON-Parse-Fehler für '{skin_name}': {e}")
        return None, None
    except Exception as e:
        print(f"Unerwarteter Fehler beim Abrufen für '{skin_name}': {e}")
        return None, None

# ═══════════════════════════════════════════════════════════════════════════════
# HAUPTFUNKTION FÜR UMFASSENDE MARKTDATEN
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_comprehensive_market_data(skin_name: str) -> Optional[MarketData]:
    """
    Ruft umfassende Marktdaten für einen CS Skin von der Steam API ab.
    
    Diese Funktion ist die Hauptschnittstelle für Marktdaten-Abfragen und sollte
    für alle neuen Implementierungen verwendet werden. Sie bietet vollständige
    Marktanalyse-Daten inklusive berechneter Metriken.
    
    Args:
        skin_name (str): Vollständiger Name des Skins
                        Format: "Waffe | Skin-Name (Condition)"
                        Beispiel: "AK-47 | Redline (Field-Tested)"
        
    Returns:
        Optional[MarketData]: MarketData-Objekt mit allen Marktinformationen
                             oder None bei Fehlern/fehlenden Daten
                             
    API-Limitations:
        - Rate-Limit: ~1 Request/Sekunde empfohlen
        - Timeout: 10 Sekunden per Request
        - Verfügbarkeit: 99%+ (Steam-abhängig)
        
    Error-Handling:
        - Netzwerk-Fehler: None + Konsolen-Log
        - API-Fehler: None + detailliertes Logging
        - Parsing-Fehler: None + Fehler-Details
        
    Performance:
        - Typische Response-Zeit: 200-800ms
        - Datenvolumen: ~200-500 Bytes per Request
        - Memory-Footprint: ~1KB per MarketData-Objekt
        
    Example:
        >>> data = fetch_comprehensive_market_data("AK-47 | Redline (Field-Tested)")
        >>> if data and data.has_valid_data:
        ...     print(f"Preis: {data.lowest_price}€")
        ...     print(f"Spread: {data.spread_percentage:.1f}%")
        ...     print(f"Volumen: {data.volume} Transaktionen")
        Preis: 24.5€
        Spread: 3.3%
        Volumen: 142 Transaktionen
    """
    # ═══════════════════════════════════════════════════════════════════════
    # INPUT-VALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    
    if not skin_name or not skin_name.strip():
        print("Error: Leerer oder ungültiger Skin-Name")
        return None
    
    # Skin-Name normalisieren (Whitespace entfernen)
    normalized_skin_name = skin_name.strip()
    
    # ═══════════════════════════════════════════════════════════════════════
    # API-REQUEST-PARAMETER
    # ═══════════════════════════════════════════════════════════════════════
    
    # Steam Community Market API Parameter
    params = {
        'appid': CSGO_APP_ID,                    # Counter-Strike: Global Offensive
        'currency': EUR_CURRENCY_ID,             # Euro Currency
        'market_hash_name': normalized_skin_name  # URL-Encoding wird von requests gemacht
    }
    
    # HTTP-Headers für bessere API-Kompatibilität
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'  # Prefer German/European formats
    }
    
    try:
        # ═══════════════════════════════════════════════════════════════════════
        # HTTP-REQUEST AUSFÜHREN
        # ═══════════════════════════════════════════════════════════════════════
        
        response = requests.get(
            STEAM_API_BASE_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        # HTTP-Status-Code prüfen (wirft Exception bei 4xx/5xx)
        response.raise_for_status()
        
        # ═══════════════════════════════════════════════════════════════════════
        # API-RESPONSE VERARBEITEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # JSON-Response parsen
        data = response.json()

        # Steam API Success-Flag validieren
        if not data.get("success"):
            print(f"Steam API Fehler für '{normalized_skin_name}': "
                  f"API returned success=false (möglicherweise Skin nicht gefunden)")
            return None
        
        # ═══════════════════════════════════════════════════════════════════════
        # MARKTDATEN EXTRAHIEREN UND PARSEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # Rohdaten von der API extrahieren
        lowest_price_raw = data.get("lowest_price", "")
        median_price_raw = data.get("median_price", "")
        volume_raw = data.get("volume", "")
        
        # String-zu-Numerisch Konvertierung
        lowest_price = _parse_price_string(lowest_price_raw)
        median_price = _parse_price_string(median_price_raw)
        volume = _parse_volume_string(volume_raw)
        
        # ═══════════════════════════════════════════════════════════════════════
        # SPREAD-METRIKEN BERECHNEN
        # ═══════════════════════════════════════════════════════════════════════
        
        # Absoluter Spread (Differenz zwischen Median und Lowest Price)
        if median_price > 0 and lowest_price > 0:
            spread_absolute = abs(median_price - lowest_price)
        else:
            spread_absolute = 0.0
        
        # Relativer Spread als Prozentsatz
        if lowest_price > 0 and spread_absolute > 0:
            spread_percentage = (spread_absolute / lowest_price) * 100
        else:
            spread_percentage = 0.0
        
        # ═══════════════════════════════════════════════════════════════════════
        # MARKTDATA-OBJEKT ERSTELLEN
        # ═══════════════════════════════════════════════════════════════════════
        
        market_data = MarketData(
            lowest_price=lowest_price,
            median_price=median_price,
            volume=volume,
            spread_absolute=spread_absolute,
            spread_percentage=spread_percentage
        )
        
        # Erfolgs-Logging für Debugging
        print(f"✅ Marktdaten erfolgreich abgerufen für '{normalized_skin_name}': {market_data}")
        
        return market_data
        
    # ═══════════════════════════════════════════════════════════════════════
    # UMFASSENDE EXCEPTION-BEHANDLUNG
    # ═══════════════════════════════════════════════════════════════════════
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout beim Abrufen für '{normalized_skin_name}' "
              f"(>{REQUEST_TIMEOUT}s) - Steam API langsam oder überlastet")
        return None
        
    except requests.exceptions.ConnectionError:
        print(f"🌐 Verbindungsfehler beim Abrufen für '{normalized_skin_name}' "
              f"- Internetverbindung oder Steam-Server prüfen")
        return None
        
    except requests.exceptions.HTTPError as e:
        # HTTP-Status-Code-spezifische Behandlung
        status_code = e.response.status_code if e.response else "unknown"
        print(f"🚫 HTTP-Fehler {status_code} beim Abrufen für '{normalized_skin_name}': {e}")
        
        if status_code == 429:
            print("💡 Rate-Limit erreicht - längere Pausen zwischen Requests empfohlen")
        elif status_code == 503:
            print("💡 Steam-Server temporär nicht verfügbar - später erneut versuchen")
            
        return None
        
    except ValueError as e:
        # JSON-Parsing oder Datenkonvertierungs-Fehler
        print(f"📊 JSON-Parse-Fehler für '{normalized_skin_name}': {e}")
        print("💡 Steam API-Response-Format möglicherweise geändert")
        return None
        
    except Exception as e:
        # Unerwartete Fehler für robuste Fehlerbehandlung
        print(f"❌ Unerwarteter Fehler beim Abrufen für '{normalized_skin_name}': {type(e).__name__}: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY-FUNKTIONEN FÜR TESTING UND DEBUGGING
# ═══════════════════════════════════════════════════════════════════════════════

def test_api_connection() -> bool:
    """
    Testet die Verbindung zur Steam API mit einem bekannten Skin.
    
    Returns:
        bool: True wenn API erreichbar, False bei Problemen
        
    Usage:
        Für Connectivity-Tests und Debugging
    """
    test_skin = "AK-47 | Redline (Field-Tested)"  # Beliebter, stabiler Skin
    
    print(f"🔍 Teste Steam API-Verbindung mit '{test_skin}'...")
    
    result = fetch_comprehensive_market_data(test_skin)
    
    if result and result.has_valid_data:
        print(f"✅ API-Verbindung erfolgreich - {result}")
        return True
    else:
        print("❌ API-Verbindung fehlgeschlagen")
        return False

def get_api_status() -> dict:
    """
    Gibt detaillierte API-Status-Informationen zurück.
    
    Returns:
        dict: Status-Informationen über die Steam API
        
    Usage:
        Für Monitoring und Debugging
    """
    status = {
        'base_url': STEAM_API_BASE_URL,
        'app_id': CSGO_APP_ID,
        'currency': EUR_CURRENCY_ID,
        'timeout': REQUEST_TIMEOUT,
        'user_agent': USER_AGENT
    }
    
    # Connectivity-Test
    status['connected'] = test_api_connection()
    
    return status

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-TESTING (bei direkter Ausführung)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test-Funktionalität bei direkter Modul-Ausführung.
    
    Usage: python fetcher.py
    """
    print("🎯 CS Skin Tracker - Market Data Fetcher Test")
    print("=" * 50)
    
    # API-Status anzeigen
    status = get_api_status()
    print(f"📊 API-Status: {status}")
    
    # Test mit verschiedenen Skins
    test_skins = [
        "AK-47 | Redline (Field-Tested)",
        "AWP | Dragon Lore (Factory New)",
        "M4A4 | Asiimov (Field-Tested)"
    ]
    
    for skin in test_skins:
        print(f"\n🔍 Teste Skin: {skin}")
        data = fetch_comprehensive_market_data(skin)
        
        if data:
            print(f"✅ Erfolgreich: {data}")
        else:
            print("❌ Fehler beim Abrufen")
    
    print("\n🏁 Test abgeschlossen")
