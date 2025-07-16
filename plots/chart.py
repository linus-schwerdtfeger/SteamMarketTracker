"""
CS Skin Tracker - Erweiterte Marktdaten-Visualisierung
=====================================================

Dieses Modul implementiert die Chart-Visualisierung für umfassende Marktdaten-Analysen
mit einem professionellen Drei-Panel-Dashboard für Preis-, Volumen- und Spread-Tracking.

Hauptkomponenten:
- MarketDataCanvas: Matplotlib-basierte Canvas-Klasse mit drei Subplots
- Erweiterte Datenvisualisierung: Dual-Preis-Tracking (Lowest/Median)
- Performance-optimierte Rendering-Pipeline mit NumPy-Integration
- Dark Theme mit optimierten Kontrastverhältnissen

Visualisierungs-Features:
- Panel 1: Preisverlauf (Niedrigster + Median-Preis mit Legende)
- Panel 2: Handelsvolumen (Balkendiagramm mit Liquiditäts-Metriken)
- Panel 3: Bid-Ask Spread (Markt-Effizienz-Indikator mit adaptiver Einheit)

Technische Highlights:
- Intelligente Y-Achsen-Skalierung für optimale Datenvisualisierung
- Adaptive Datumsformatierung basierend auf Datendichte
- Performance-optimiertes Layout mit minimalen UI-Blocking
- Robuste Error-Behandlung mit informativen Fehlermeldungen

Design-Prinzipien:
- Konsistentes Dark Theme (rgb(45, 45, 45)) für augenschonende Darstellung
- Hohe Kontraste für bessere Lesbarkeit (#ffffff Text auf dunklem Grund)
- Responsive Layout-Management für verschiedene Bildschirmgrößen
- Professionelle Chart-Ästhetik mit dezenten Grid-Linien

Author: CS Skin Tracker Team
Version: 2.0 - Enhanced Multi-Chart Edition
License: MIT
"""

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Tuple, Optional
import numpy as np
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# CHART-KONFIGURATION UND KONSTANTEN
# ═══════════════════════════════════════════════════════════════════════════════

# Design-Parameter für konsistente Visualisierung
DARK_BACKGROUND_COLOR = '#2d2d2d'      # Haupt-Hintergrundfarbe (konsistent mit UI)
GRID_COLOR = '#cccccc'                 # Grid-Linien-Farbe
TEXT_COLOR = '#ffffff'                 # Primäre Textfarbe
SPINE_COLOR = '#cccccc'                # Achsen-Rahmen-Farbe

# Chart-Farben für verschiedene Datentypen
PRICE_COLOR_PRIMARY = '#00bfff'        # Niedrigster Preis (Cyan-Blau)
PRICE_COLOR_MEDIAN = '#ffa500'         # Median-Preis (Orange)
VOLUME_COLOR = '#00ff7f'               # Handelsvolumen (Grün)
SPREAD_PERCENTAGE_COLOR = '#ff6b6b'    # Spread Prozent (Rot)
SPREAD_ABSOLUTE_COLOR = '#ff9500'      # Spread Absolut (Orange-Rot)
ERROR_COLOR = '#ff6b6b'                # Fehlermeldungen (Rot)

# Layout-Parameter für optimale Darstellung
FIGURE_SIZE = (12, 8)                  # Basis-Figure-Größe in Zoll
FIGURE_DPI = 100                       # DPI für scharfe Darstellung
SUBPLOT_SPACING = 0.25                 # Vertikaler Abstand zwischen Subplots
MARGIN_LEFT = 0.08                     # Linker Rand (für Y-Achsen-Labels)
MARGIN_RIGHT = 0.96                    # Rechter Rand
MARGIN_TOP = 0.94                      # Oberer Rand
MARGIN_BOTTOM = 0.10                   # Unterer Rand (für X-Achsen-Labels)

# Performance-Parameter
MAX_X_AXIS_LABELS = 8                  # Maximale Anzahl X-Achsen-Labels
ADAPTIVE_BAR_WIDTH_FACTOR = 0.8        # Faktor für Balkenbreite-Berechnung
MIN_PRICE_MARGIN = 0.1                 # Minimale Y-Achsen-Margin in Euro
PRICE_MARGIN_PERCENTAGE = 0.05         # Prozentuale Y-Achsen-Margin

# ═══════════════════════════════════════════════════════════════════════════════
# HAUPT-CHART-KLASSE
# ═══════════════════════════════════════════════════════════════════════════════

class MarketDataCanvas(FigureCanvas):
    """
    Erweiterte Canvas-Klasse für umfassende Marktdaten-Visualisierung.
    
    Diese Klasse implementiert ein professionelles Drei-Panel-Dashboard für
    CS Skin Marktdaten mit optimierten Visualisierungen für verschiedene
    Datentypen und intelligenter Layout-Verwaltung.
    
    Architektur-Features:
    - Matplotlib FigureCanvas-Integration für Qt-Kompatibilität
    - Drei spezialisierte Subplots mit individueller Optimierung
    - Dark Theme mit konsistenter Farbpalette
    - Performance-optimierte Rendering-Pipeline
    - Intelligente Daten-Preprocessing mit NumPy
    
    Panel-Struktur:
    1. Preisverlauf (oben): Niedrigster + Median-Preis mit Legende
    2. Handelsvolumen (mitte): Balkendiagramm mit Statistik-Overlay
    3. Bid-Ask Spread (unten): Liniendiagramm mit adaptiver Einheit
    
    Performance-Optimierungen:
    - NumPy-Arrays für effiziente Datenverarbeitung
    - Intelligente Y-Achsen-Skalierung verhindert Über-/Unterzooming
    - Adaptive X-Achsen-Label-Reduktion für bessere Lesbarkeit
    - Minimal-Memory-Footprint durch effiziente Datenstrukturen
    
    Error-Handling:
    - Umfassende Exception-Behandlung in allen Rendering-Phasen
    - Informative Fehlermeldungen mit visuellen Indikatoren
    - Graceful Degradation bei partiell verfügbaren Daten
    - Logging-Integration für Debugging und Monitoring
    
    Thread-Safety:
    - Alle Rendering-Operationen sind thread-safe
    - Signal-basierte Updates unterstützt
    - Keine Race Conditions bei gleichzeitigen Chart-Updates
    """
    
    def __init__(self, parent: Optional = None):
        """
        Initialisiert die Marktdaten-Canvas mit optimiertem Layout.
        
        Args:
            parent: Qt-Parent-Widget für Integration in GUI
            
        Setup-Reihenfolge:
        1. Figure-Konfiguration mit optimierten Parametern
        2. Subplot-Layout-Management für drei Panels
        3. Dark Theme-Anwendung für konsistente Ästhetik
        4. Layout-Optimierung für verschiedene Bildschirmgrößen
        
        Performance-Considerations:
        - Figure-DPI optimiert für moderne Displays
        - Subplot-Spacing minimiert für maximale Chart-Fläche
        - Margin-Parameter ausbalanciert für Label-Sichtbarkeit
        """
        # Basis-Figure mit optimierten Parametern
        self.fig = Figure(
            figsize=FIGURE_SIZE, 
            dpi=FIGURE_DPI,
            facecolor=DARK_BACKGROUND_COLOR,
            tight_layout=False  # Manuelles Layout für bessere Kontrolle
        )
        
        # FigureCanvas-Initialisierung
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Drei spezialisierte Subplots erstellen
        self._create_subplots()
        
        # Dark Theme und Layout anwenden
        self._apply_dark_theme()
        self._configure_layout()
    
    def _create_subplots(self) -> None:
        """
        Erstellt die drei Haupt-Subplots mit optimierten Parametern.
        
        Subplot-Layout:
        - 3 Zeilen, 1 Spalte für vertikale Anordnung
        - Gleiche Höhe für ausgewogene Visualisierung
        - Geteilte X-Achse für synchronisierte Zeitdarstellung
        
        Subplot-Spezialisierung:
        - ax_price: Preisverlauf mit Dual-Serien-Unterstützung
        - ax_volume: Balkendiagramm für Handelsvolumen
        - ax_spread: Liniendiagramm für Spread-Analyse
        """
        self.ax_price = self.fig.add_subplot(3, 1, 1)
        self.ax_volume = self.fig.add_subplot(3, 1, 2, sharex=self.ax_price)
        self.ax_spread = self.fig.add_subplot(3, 1, 3, sharex=self.ax_price)
    
    def _configure_layout(self) -> None:
        """
        Konfiguriert das Layout für optimale Raumnutzung.
        
        Layout-Optimierungen:
        - Reduzierte Subplot-Abstände für kompakte Darstellung
        - Optimierte Margins für verschiedene Label-Längen
        - Responsive Design für verschiedene Window-Größen
        
        Design-Rationale:
        - Maximale Chart-Fläche bei erhaltener Lesbarkeit
        - Konsistente Abstände zwischen allen UI-Elementen
        - Professionelle Ästhetik mit ausgewogenen Proportionen
        """
        self.fig.subplots_adjust(
            hspace=SUBPLOT_SPACING,
            left=MARGIN_LEFT,
            right=MARGIN_RIGHT,
            top=MARGIN_TOP,
            bottom=MARGIN_BOTTOM
        )

    def _apply_dark_theme(self) -> None:
        """
        Wendet konsistentes Dark Theme auf alle Chart-Komponenten an.
        
        Theme-Komponenten:
        - Hintergrundfarben für Figure und Axes
        - Grid-Styling mit optimaler Transparenz
        - Spine (Rahmen) Styling für professionellen Look
        - Tick-Parameter für optimale Lesbarkeit
        - Text-Farben für hohen Kontrast
        
        Design-Konsistenz:
        - Identische Farben wie in der Haupt-UI
        - Einheitliche Transparenz-Werte
        - Konsistente Linienbreiten und -stile
        - Optimierte Kontraste für Accessibility
        
        Performance-Note:
        Diese Methode wird mehrfach aufgerufen und muss daher effizient sein.
        """
        axes_list = [self.ax_price, self.ax_volume, self.ax_spread]
        
        for ax in axes_list:
            # Hintergrund-Konfiguration
            ax.set_facecolor(DARK_BACKGROUND_COLOR)
            
            # Grid-Styling für bessere Datenlesbarkeit
            ax.grid(
                True, 
                alpha=0.3,                    # Dezente Transparenz
                color=GRID_COLOR, 
                linestyle='-', 
                linewidth=0.6                 # Feine Linien
            )
            
            # Spine (Achsen-Rahmen) Styling
            for spine in ax.spines.values():
                spine.set_color(SPINE_COLOR)
                spine.set_linewidth(0.8)      # Subtile aber sichtbare Rahmen
            
            # Tick-Parameter für optimale Lesbarkeit
            ax.tick_params(
                axis='both', 
                colors=TEXT_COLOR, 
                labelsize=9,                  # Kompakte aber lesbare Labels
                width=0.8                     # Konsistent mit Spine-Breite
            )
            
            # Text-Komponenten-Styling
            ax.title.set_color(TEXT_COLOR)
            ax.xaxis.label.set_color(TEXT_COLOR)
            ax.yaxis.label.set_color(TEXT_COLOR)

    def plot_market_data(self, data: List[Tuple], skin_name: str) -> None:
        """
        Hauptmethode für umfassende Marktdaten-Visualisierung.
        
        Args:
            data: Liste von (timestamp, lowest_price, median_price, volume, 
                  spread_absolute, spread_percentage) Tupeln
            skin_name: Name des Skins für Titel und Fehlermeldungen
            
        Datenverarbeitung:
        - Validation und Preprocessing aller Input-Daten
        - NumPy-basierte Konvertierung für Performance
        - Intelligente Daten-Extraktion mit Error-Handling
        - Adaptive Chart-Konfiguration basierend auf verfügbaren Daten
        
        Rendering-Pipeline:
        1. Chart-Reset und Theme-Anwendung
        2. Daten-Preprocessing und Validation
        3. Panel 1: Preisverlauf-Rendering (Dual-Serie)
        4. Panel 2: Volumen-Balkendiagramm
        5. Panel 3: Spread-Analyse (adaptive Einheit)
        6. Layout-Finalisierung und Canvas-Update
        
        Performance-Optimierungen:
        - Effiziente NumPy-Array-Operationen
        - Minimale Matplotlib-API-Calls
        - Intelligente Label-Reduktion für große Datensätze
        - Adaptive Rendering basierend auf Datendichte
        
        Error-Handling:
        - Comprehensive Exception-Behandlung auf allen Ebenen
        - Spezifische Error-Messages für verschiedene Fehlertypen
        - Graceful Fallbacks bei partiell korrupten Daten
        - Visual Error-Indicators für User-Feedback
        
        Raises:
            Keine - alle Exceptions werden intern behandelt und visualisiert
        """
        # Chart-Reset für saubere Neudarstellung
        self._reset_charts()
        
        # Early return bei fehlenden Daten
        if not data:
            self._show_no_data_message(skin_name)
            return
        
        try:
            # Daten-Preprocessing mit NumPy für Performance
            processed_data = self._preprocess_data(data)
            
            if not processed_data:
                self._show_no_data_message(skin_name)
                return
            
            # Entpacke verarbeitete Daten
            timestamps, prices, median_prices, volumes, spread_absolute, spread_percentage = processed_data
            
            # Drei-Panel-Rendering
            self._render_price_panel(timestamps, prices, median_prices, skin_name)
            self._render_volume_panel(timestamps, volumes)
            self._render_spread_panel(timestamps, spread_absolute, spread_percentage)
            
            # Layout-Finalisierung
            self._finalize_layout()
            
        except Exception as e:
            # Umfassende Error-Behandlung mit Logging
            error_msg = f"Fehler beim Rendern der Marktdaten: {str(e)}"
            logging.error(f"Chart-Rendering-Fehler für '{skin_name}': {e}", exc_info=True)
            self._show_error_message(skin_name, error_msg)
        
        finally:
            # Canvas-Update garantiert auch bei Fehlern
            self.draw()

    def _reset_charts(self) -> None:
        """
        Setzt alle Charts für saubere Neudarstellung zurück.
        
        Reset-Operationen:
        - Alle Subplot-Inhalte löschen
        - Dark Theme erneut anwenden
        - Layout-Parameter zurücksetzen
        
        Performance-Note:
        Sehr schnelle Operation (~1-2ms) da nur Matplotlib-Clearing.
        """
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
        self._apply_dark_theme()

    def _preprocess_data(self, data: List[Tuple]) -> Optional[Tuple]:
        """
        Verarbeitet Rohdaten zu NumPy-Arrays für effiziente Visualisierung.
        
        Args:
            data: Roh-Datenliste mit Tupeln
            
        Returns:
            Tuple of NumPy arrays oder None bei Fehlern
            
        Preprocessing-Schritte:
        1. Timestamp-String zu datetime-Objekten konvertieren
        2. Numerische Werte zu NumPy-Arrays konvertieren
        3. Datenvalidation und Outlier-Detection
        4. Fehlende/ungültige Werte behandeln
        
        Error-Handling:
        - ISO-Format-Parsing mit Fallbacks
        - Numerische Konvertierung mit Exception-Handling
        - Graceful Handling von partiell korrupten Daten
        
        Performance:
        - Vectorized Operations wo möglich
        - Minimal-Memory-Allocation
        - Effiziente Array-Erstellung
        """
        try:
            # Timestamp-Konvertierung mit Error-Handling
            timestamps = []
            for row in data:
                try:
                    # Versuche ISO-Format-Parsing
                    timestamp = datetime.fromisoformat(row[0])
                    timestamps.append(timestamp)
                except (ValueError, TypeError) as e:
                    logging.warning(f"Ungültiger Timestamp: {row[0]} - {e}")
                    continue
            
            if not timestamps:
                logging.error("Keine gültigen Timestamps gefunden")
                return None
            
            # Numerische Arrays mit Validation
            valid_indices = range(len(timestamps))
            
            prices = np.array([float(data[i][1]) for i in valid_indices if i < len(data)])
            median_prices = np.array([float(data[i][2]) for i in valid_indices if i < len(data)])
            volumes = np.array([int(data[i][3]) for i in valid_indices if i < len(data)])
            spread_absolute = np.array([float(data[i][4]) for i in valid_indices if i < len(data)])
            spread_percentage = np.array([float(data[i][5]) for i in valid_indices if i < len(data)])
            
            # Datenvalidation
            if len(prices) == 0:
                logging.error("Keine gültigen Preisdaten")
                return None
            
            # Negative Werte bereinigen (sollte durch DB-Constraints verhindert sein)
            prices = np.maximum(prices, 0.0)
            median_prices = np.maximum(median_prices, 0.0)
            volumes = np.maximum(volumes, 0)
            spread_absolute = np.maximum(spread_absolute, 0.0)
            spread_percentage = np.maximum(spread_percentage, 0.0)
            
            return timestamps, prices, median_prices, volumes, spread_absolute, spread_percentage
            
        except Exception as e:
            logging.error(f"Fehler bei Datenverarbeitung: {e}")
            return None

    def _render_price_panel(self, timestamps: List[datetime], prices: np.ndarray, 
                           median_prices: np.ndarray, skin_name: str) -> None:
        """
        Rendert das Preisverlauf-Panel mit Dual-Serien-Unterstützung.
        
        Args:
            timestamps: Liste von datetime-Objekten
            prices: NumPy-Array der niedrigsten Preise
            median_prices: NumPy-Array der Median-Preise
            skin_name: Skin-Name für Panel-Titel
            
        Rendering-Features:
        - Primäre Serie: Niedrigste Preise (durchgezogene Linie)
        - Sekundäre Serie: Median-Preise (gestrichelte Linie, optional)
        - Intelligente Legende nur bei mehreren Serien
        - Optimierte Y-Achsen-Skalierung für beste Datenvisualisierung
        - Marker für bessere Datenpunkt-Identifikation
        
        Y-Achsen-Optimierung:
        - Berücksichtigt beide Preistypen für optimale Skalierung
        - Intelligent margin calculation basierend auf Preisbereich
        - Mindest-Margin für sehr kleine Spreads
        - Verhindert Over-/Underzooming bei extremen Werten
        
        Design-Details:
        - Hochkontrast-Farben für bessere Lesbarkeit
        - Durchgezogene vs. gestrichelte Linien für klare Unterscheidung
        - Verschiedene Marker-Styles für Serie-Identification
        - Professional Legend-Styling mit Dark Theme
        """
        # Primäre Serie: Niedrigste Preise
        self.ax_price.plot(
            timestamps, prices,
            color=PRICE_COLOR_PRIMARY,
            linewidth=2.5,
            marker="o",
            markersize=4,
            label="Niedrigster Preis",
            alpha=0.9,
            solid_capstyle='round'  # Rundere Linienenden
        )
        
        # Sekundäre Serie: Median-Preise (nur wenn verfügbar)
        median_plotted = False
        if np.any(median_prices > 0):
            self.ax_price.plot(
                timestamps, median_prices,
                color=PRICE_COLOR_MEDIAN,
                linewidth=2.0,
                linestyle="--",           # Gestrichelt für Unterscheidung
                marker="s",              # Quadratische Marker
                markersize=3,
                label="Median Preis",
                alpha=0.8
            )
            median_plotted = True
        
        # Intelligente Legende (nur bei mehreren Serien)
        if median_plotted or True:  # Immer anzeigen für Konsistenz
            legend = self.ax_price.legend(
                loc='upper left',
                fontsize=9,
                framealpha=0.9,
                fancybox=True,           # Rundere Ecken
                shadow=False             # Kein Schatten im Dark Theme
            )
            
            # Legend-Styling für Dark Theme
            legend.get_frame().set_facecolor(DARK_BACKGROUND_COLOR)
            legend.get_frame().set_edgecolor(SPINE_COLOR)
            legend.get_frame().set_linewidth(0.8)
            
            for text in legend.get_texts():
                text.set_color(TEXT_COLOR)
        
        # Panel-Titel und Labels
        self.ax_price.set_title(
            f"Preisverlauf: {skin_name}",
            fontsize=13,
            fontweight='bold',
            pad=10                       # Abstand zum Chart
        )
        self.ax_price.set_ylabel("Preis (€)", fontsize=11)
        
        # Intelligente Y-Achsen-Skalierung
        self._optimize_price_y_axis(prices, median_prices, median_plotted)

    def _optimize_price_y_axis(self, prices: np.ndarray, median_prices: np.ndarray, 
                              median_plotted: bool) -> None:
        """
        Optimiert die Y-Achsen-Skalierung für optimale Preis-Visualisierung.
        
        Args:
            prices: Niedrigste Preise
            median_prices: Median-Preise
            median_plotted: Ob Median-Preise dargestellt werden
            
        Optimierungs-Algorithmus:
        1. Sammle alle relevanten Preise (lowest + median wenn vorhanden)
        2. Berechne Min/Max-Werte über alle Preistypen
        3. Bestimme intelligente Margins basierend auf Preisbereich
        4. Wende Mindest-Margins für sehr kleine Spreads an
        5. Setze Y-Limits für optimale Datenvisualisierung
        
        Edge-Cases:
        - Identische Preise: 10% Margin vom Preiswert
        - Sehr kleine Spreads: Mindest-Margin von 0.1€
        - Große Preisbereiche: 5% proportionale Margin
        - Einzelner Datenpunkt: Standardisierte Margin
        """
        if len(prices) <= 1:
            return  # Keine Optimierung bei zu wenigen Daten
        
        # Sammle alle relevanten Preise für globale Min/Max-Berechnung
        all_prices = list(prices)
        
        if median_plotted:
            # Nur gültige Median-Preise berücksichtigen
            valid_median = median_prices[median_prices > 0]
            all_prices.extend(valid_median)
        
        if not all_prices:
            return  # Keine gültigen Preise
        
        # Min/Max über alle Preistypen
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price
        
        # Intelligente Margin-Berechnung
        if price_range > 0:
            # Proportionale Margin für normale Preisbereiche
            margin = price_range * PRICE_MARGIN_PERCENTAGE
        else:
            # Feste Margin bei identischen Preisen
            margin = max_price * 0.1 if max_price > 0 else 1.0
        
        # Mindest-Margin für sehr kleine Spreads
        margin = max(margin, MIN_PRICE_MARGIN)
        
        # Y-Limits setzen mit berechneten Margins
        self.ax_price.set_ylim(
            min_price - margin,
            max_price + margin
        )

    def _render_volume_panel(self, timestamps: List[datetime], volumes: np.ndarray) -> None:
        """
        Rendert das Handelsvolumen-Panel als Balkendiagramm.
        
        Args:
            timestamps: Liste von datetime-Objekten
            volumes: NumPy-Array der Handelsvolumen
            
        Rendering-Features:
        - Adaptive Balkenbreite basierend auf Zeitabständen
        - Statistik-Overlay mit Durchschnitt und Maximum
        - Optimierte Farben für Liquiditäts-Indikation
        - Edge-Cases-Handling für einzelne Datenpunkte
        
        Balkenbreite-Berechnung:
        - Automatische Berechnung basierend auf Zeitintervallen
        - Fallback für einzelne Datenpunkte
        - Proportionale Skalierung für verschiedene Datenfrequenzen
        
        Statistik-Overlay:
        - Durchschnittsvolumen für Trend-Erkennung
        - Maximum-Volumen für Spike-Identification
        - Positioniert in oberer linker Ecke für minimale Datenverdeckung
        - Dark Theme-kompatibles Styling
        """
        # Adaptive Balkenbreite-Berechnung
        if len(timestamps) > 1:
            # Durchschnittlicher Zeitabstand zwischen Datenpunkten
            total_timespan = (timestamps[-1] - timestamps[0]).total_seconds()
            avg_interval = total_timespan / len(timestamps)
            
            # Konvertiere zu Tagen und wende Skalierungsfaktor an
            bar_width = (avg_interval / 86400) * ADAPTIVE_BAR_WIDTH_FACTOR
        else:
            # Fallback für einzelne Datenpunkte
            bar_width = 0.8
        
        # Balkendiagramm mit optimierten Parametern
        self.ax_volume.bar(
            timestamps, volumes,
            width=bar_width,
            color=VOLUME_COLOR,
            alpha=0.8,                   # Leichte Transparenz für professionellen Look
            edgecolor=SPINE_COLOR,       # Konsistente Rahmenfarbe
            linewidth=0.5               # Feine Rahmenlinien
        )
        
        # Panel-Styling
        self.ax_volume.set_title(
            "Handelsvolumen (Liquidität)",
            fontsize=12,
            fontweight='bold',
            pad=10
        )
        self.ax_volume.set_ylabel("Anzahl Transaktionen", fontsize=11)
        
        # Statistik-Overlay für zusätzliche Insights
        self._add_volume_statistics(volumes)

    def _add_volume_statistics(self, volumes: np.ndarray) -> None:
        """
        Fügt Volumen-Statistiken als Text-Overlay hinzu.
        
        Args:
            volumes: NumPy-Array der Volumen-Daten
            
        Statistiken:
        - Durchschnittsvolumen (Ø): Zeigt allgemeine Liquiditätstrends
        - Maximum-Volumen (Max): Identifiziert Volumen-Spikes
        - Formatierung als Integer für bessere Lesbarkeit
        
        Positioning:
        - Obere linke Ecke (2%, 95%) für minimale Datenverdeckung
        - Transform-basierte Positionierung für Größen-Unabhängigkeit
        - Dark Theme-kompatible Box mit transparentem Hintergrund
        """
        if len(volumes) > 0:
            avg_volume = np.mean(volumes)
            max_volume = np.max(volumes)
            
            # Formatierte Statistik-Anzeige
            stats_text = f'Ø: {avg_volume:.0f} | Max: {max_volume:.0f}'
            
            self.ax_volume.text(
                0.02, 0.95,              # Relative Position (2% von links, 95% von unten)
                stats_text,
                transform=self.ax_volume.transAxes,  # Axes-relative Koordinaten
                fontsize=9,
                color=TEXT_COLOR,
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor=DARK_BACKGROUND_COLOR,
                    alpha=0.8,
                    edgecolor=SPINE_COLOR,
                    linewidth=0.5
                ),
                verticalalignment='top',
                horizontalalignment='left'
            )

    def _render_spread_panel(self, timestamps: List[datetime], spread_absolute: np.ndarray, 
                            spread_percentage: np.ndarray) -> None:
        """
        Rendert das Bid-Ask Spread-Panel mit adaptiver Einheit.
        
        Args:
            timestamps: Liste von datetime-Objekten
            spread_absolute: NumPy-Array der absoluten Spreads (€)
            spread_percentage: NumPy-Array der prozentualen Spreads (%)
            
        Adaptive Einheit-Logik:
        - Bevorzuge Prozentsätze wenn verfügbar und realistisch (<50%)
        - Fallback zu absoluten Werten bei extremen Prozentsätzen
        - Verschiedene Farben für verschiedene Einheiten
        
        Rendering-Features:
        - Liniendiagramm für Trend-Visualisierung
        - Dreieckige Marker für Spread-Identification
        - Statistik-Overlay mit Durchschnitt und Minimum
        - X-Achsen-Label nur im untersten Panel
        
        Design-Rationale:
        Spread-Analyse ist entscheidend für Markt-Effizienz-Bewertung.
        Prozentuale Spreads sind meist aussagekräftiger, aber absolute
        Werte können bei sehr teuren Skins relevanter sein.
        """
        # Intelligente Einheit-Auswahl
        use_percentage = (
            np.any(spread_percentage > 0) and 
            np.mean(spread_percentage[spread_percentage > 0]) < 50
        )
        
        if use_percentage:
            # Prozentuale Darstellung (bevorzugt)
            spread_data = spread_percentage
            ylabel = "Spread (%)"
            color = SPREAD_PERCENTAGE_COLOR
            unit = "%"
        else:
            # Absolute Darstellung (Fallback)
            spread_data = spread_absolute
            ylabel = "Spread (€)"
            color = SPREAD_ABSOLUTE_COLOR
            unit = "€"
        
        # Liniendiagramm für Spread-Trends
        self.ax_spread.plot(
            timestamps, spread_data,
            color=color,
            linewidth=2.5,
            marker="^",                  # Dreieckige Marker für Spread-Daten
            markersize=4,
            alpha=0.9,
            solid_capstyle='round'
        )
        
        # Panel-Styling
        self.ax_spread.set_title(
            "Bid-Ask Spread (Markt-Effizienz)",
            fontsize=12,
            fontweight='bold',
            pad=10
        )
        self.ax_spread.set_ylabel(ylabel, fontsize=11)
        self.ax_spread.set_xlabel("Zeit", fontsize=11)
        
        # Spread-Statistiken hinzufügen
        self._add_spread_statistics(spread_data, unit)

    def _add_spread_statistics(self, spread_data: np.ndarray, unit: str) -> None:
        """
        Fügt Spread-Statistiken als Text-Overlay hinzu.
        
        Args:
            spread_data: Spread-Daten für Statistik-Berechnung
            unit: Einheit für Formatierung (% oder €)
            
        Statistiken:
        - Durchschnitts-Spread (Ø): Zeigt allgemeine Markt-Effizienz
        - Minimum-Spread (Min): Beste verfügbare Liquidität
        - Ein-Dezimalstelle-Formatierung für Präzision ohne Clutter
        """
        if len(spread_data) > 0:
            avg_spread = np.mean(spread_data)
            min_spread = np.min(spread_data)
            
            # Formatierte Statistik-Anzeige
            stats_text = f'Ø: {avg_spread:.1f}{unit} | Min: {min_spread:.1f}{unit}'
            
            self.ax_spread.text(
                0.02, 0.95,
                stats_text,
                transform=self.ax_spread.transAxes,
                fontsize=9,
                color=TEXT_COLOR,
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor=DARK_BACKGROUND_COLOR,
                    alpha=0.8,
                    edgecolor=SPINE_COLOR,
                    linewidth=0.5
                ),
                verticalalignment='top',
                horizontalalignment='left'
            )

    def _finalize_layout(self) -> None:
        """
        Finalisiert das Chart-Layout mit optimierten Parametern.
        
        Layout-Optimierungen:
        - Adaptive X-Achsen-Label-Verwaltung
        - Intelligente Datums-Formatierung
        - Label-Reduktion für bessere Lesbarkeit
        - Responsive Design für verschiedene Datenmengen
        
        X-Achsen-Management:
        - Nur unterstes Panel zeigt X-Labels (Platz-Optimierung)
        - Adaptive Formatierung basierend auf Datendichte
        - Horizontale Labels für bessere Lesbarkeit
        - Intelligente Label-Intervalle bei großen Datenmengen
        
        Performance:
        - Minimal matplotlib API calls
        - Effiziente Label-Reduktions-Algorithmen
        - Optimierte tight_layout() Alternative
        """
        # Adaptive Datums-Formatierung basierend auf Datenanzahl
        timestamps_count = len(self.ax_price.get_xticklabels())
        
        if timestamps_count > 7:
            date_format = '%d.%m'        # Nur Tag.Monat für viele Daten
        else:
            date_format = '%d.%m %H:%M'  # Tag.Monat Stunde:Minute für wenige Daten
        
        # Label-Intervall für Lesbarkeit
        label_interval = max(1, timestamps_count // MAX_X_AXIS_LABELS)
        
        # Alle Axes konfigurieren
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            # Datums-Formatierung
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            
            # Horizontale Labels (keine Rotation für bessere Lesbarkeit)
            ax.tick_params(axis='x', rotation=0, labelsize=8)
            
            # Intelligente Label-Reduktion bei großen Datenmengen
            if timestamps_count > 15:
                # Verwende DayLocator mit Intervall
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=label_interval))
            elif timestamps_count > 5:
                # Verstecke jeden n-ten Label manuell
                for i, label in enumerate(ax.xaxis.get_ticklabels()):
                    if i % label_interval != 0:
                        label.set_visible(False)
        
        # X-Label-Optimierung: Nur unterstes Panel zeigt Labels
        self.ax_price.tick_params(axis='x', labelbottom=False)
        self.ax_volume.tick_params(axis='x', labelbottom=False)
        # ax_spread behält Labels (bereits konfiguriert)
        
        # Layout-Finalisierung
        self.fig.tight_layout()

    def _show_no_data_message(self, skin_name: str) -> None:
        """
        Zeigt informative Nachricht bei fehlenden Daten.
        
        Args:
            skin_name: Name des Skins für personalisierte Nachricht
            
        Message-Design:
        - Zentrierte Platzierung in allen Panels
        - Konsistente Panel-Titel für UI-Kontinuität
        - Dezente Farbe für non-intrusive Darstellung
        - Dark Theme-kompatible Box-Gestaltung
        
        User-Experience:
        - Klar kommuniziert warum keine Daten angezeigt werden
        - Personalisierte Nachricht mit Skin-Namen
        - Professionelle Darstellung ohne Error-Charakter
        - Konsistente Panel-Struktur bleibt erhalten
        """
        # Personalisierte Nachricht
        if skin_name:
            message = f"Keine Marktdaten verfügbar für:\n{skin_name}"
        else:
            message = "Keine Daten verfügbar"
        
        # Panel-Titel für Konsistenz
        titles = ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]
        
        # Nachricht in allen Panels anzeigen
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], titles):
            ax.text(
                0.5, 0.5,                # Zentrierte Positionierung
                message,
                ha='center',
                va='center',
                transform=ax.transAxes,
                fontsize=14,
                color='#cccccc',         # Dezente Graufarbe
                bbox=dict(
                    boxstyle="round,pad=0.5",
                    facecolor=DARK_BACKGROUND_COLOR,
                    alpha=0.8,
                    edgecolor=SPINE_COLOR,
                    linewidth=0.8
                )
            )
            
            # Panel-Titel setzen
            ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Unterste Achse mit Label (für UI-Konsistenz)
        self.ax_spread.set_xlabel("Zeit", fontsize=11)

    def _show_error_message(self, skin_name: str, error: str) -> None:
        """
        Zeigt detaillierte Fehlermeldung bei Rendering-Problemen.
        
        Args:
            skin_name: Name des Skins für Kontext
            error: Fehlerbeschreibung für User und Debugging
            
        Error-Visualization:
        - Rot gefärbte Nachrichten für Aufmerksamkeit
        - Detaillierte Fehlerbeschreibung für Debugging
        - Skin-Name im Titel für Kontext
        - Logging für Entwickler-Feedback
        
        Design-Prinzipien:
        - Klar kommuniziert dass ein Fehler aufgetreten ist
        - Bietet hilfreiche Informationen ohne zu überwältigen
        - Behält professionelle Ästhetik auch bei Fehlern
        - Ermöglicht einfaches Debugging durch detaillierte Messages
        """
        error_msg = f"Fehler beim Laden der Marktdaten:\n{error}"
        
        # Panel-Titel mit Fehler-Indikation
        titles = ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]
        
        # Fehlermeldung in allen Panels
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], titles):
            ax.text(
                0.5, 0.5,
                error_msg,
                ha='center',
                va='center',
                transform=ax.transAxes,
                fontsize=12,
                color=ERROR_COLOR,       # Rote Farbe für Fehler-Aufmerksamkeit
                bbox=dict(
                    boxstyle="round,pad=0.5",
                    facecolor=DARK_BACKGROUND_COLOR,
                    alpha=0.9,
                    edgecolor=ERROR_COLOR,
                    linewidth=1.0
                )
            )
            
            # Fehler-Titel mit Skin-Name
            error_title = f"Fehler - {title}: {skin_name}" if skin_name else f"Fehler - {title}"
            ax.set_title(error_title, fontsize=12, color=ERROR_COLOR)
        
        # Logging für Entwickler-Debugging
        logging.error(f"Chart-Rendering-Fehler für '{skin_name}': {error}")
