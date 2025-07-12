from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Tuple, Optional
import numpy as np

class EnhancedPricePlotCanvas(FigureCanvas):
    """Canvas für die Darstellung von Preisverläufen, Volumen und Spread als Matplotlib-Plot."""
    
    def __init__(self, parent=None):
        # Dynamische Größe - wird automatisch an Container angepasst
        self.fig = Figure(figsize=(10, 6), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Dunkler Hintergrund für Figure
        self.fig.patch.set_facecolor('#2d2d2d')  # RGB: 45, 45, 45
        
        # Erstelle drei Subplots: Preis, Volume, Spread
        self.ax_price = self.fig.add_subplot(3, 1, 1)  # Preisverlauf
        self.ax_volume = self.fig.add_subplot(3, 1, 2)  # Volumen (Balken)
        self.ax_spread = self.fig.add_subplot(3, 1, 3)  # Spread (Linie)
        
        # Dunkler Stil für alle Subplots
        self._apply_dark_theme()
        
        # Bessere Größenanpassung
        self.fig.subplots_adjust(hspace=0.4, left=0.1, right=0.95, top=0.95, bottom=0.1)

    def _apply_dark_theme(self):
        """Wendet dunkles Design auf alle Plots an."""
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            # Hintergrund der Plots
            ax.set_facecolor('#2d2d2d')  # RGB: 45, 45, 45
            
            # Grid in hellerem Grau für bessere Sichtbarkeit
            ax.grid(True, alpha=0.3, color='#cccccc', linestyle='-', linewidth=0.8)
            
            # Achsen-Farben
            ax.spines['bottom'].set_color('#cccccc')
            ax.spines['top'].set_color('#cccccc') 
            ax.spines['right'].set_color('#cccccc')
            ax.spines['left'].set_color('#cccccc')
            
            # Tick-Farben (Zahlen und Beschriftungen)
            ax.tick_params(axis='both', colors='#ffffff', labelsize=8)
            
            # Titel- und Label-Farben
            ax.title.set_color('#ffffff')
            ax.xaxis.label.set_color('#ffffff')
            ax.yaxis.label.set_color('#ffffff')

    def plot_comprehensive(self, data: List[Tuple], skin_name: str):
        """
        Zeichnet umfassende Marktdaten (Preis, Volumen, Spread).
        
        Args:
            data: Liste von (timestamp, price, median_price, volume, spread_absolute, spread_percentage) Tupeln
            skin_name: Name des Skins für den Titel
        """
        # Alle Subplots leeren und dunkles Theme anwenden
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
        self._apply_dark_theme()
        
        if not data:
            self._show_no_data_message(skin_name)
            return

        try:
            # Daten extrahieren
            timestamps = [datetime.fromisoformat(row[0]) for row in data]
            prices = [row[1] for row in data]
            median_prices = [row[2] for row in data]
            volumes = [row[3] for row in data]
            spread_absolute = [row[4] for row in data]
            spread_percentage = [row[5] for row in data]
            
            # 1. Preisverlauf (mit Median-Preis) - Helle Farben für Kontrast
            self.ax_price.plot(timestamps, prices, marker="o", linestyle="-", 
                              color="#00bfff", linewidth=2, markersize=3, label="Niedrigster Preis")  # Cyan-Blau
            if any(mp > 0 for mp in median_prices):
                self.ax_price.plot(timestamps, median_prices, marker="s", linestyle="--", 
                                  color="#ffa500", linewidth=1.5, markersize=2, label="Median Preis")  # Orange
                legend = self.ax_price.legend(fontsize=8)
                legend.get_frame().set_facecolor('#2d2d2d')
                legend.get_frame().set_edgecolor('#cccccc')
                for text in legend.get_texts():
                    text.set_color('#ffffff')
            
            self.ax_price.set_title(f"Preisverlauf: {skin_name}", fontsize=12, fontweight='bold', color='#ffffff')
            self.ax_price.set_ylabel("Preis (€)", fontsize=10, color='#ffffff')
            
            # 2. Handelsvolumen (Balkendiagramm) - Grün für Volumen
            bar_width = (timestamps[-1] - timestamps[0]).total_seconds() / (len(timestamps) * 86400 * 2) if len(timestamps) > 1 else 1
            self.ax_volume.bar(timestamps, volumes, width=bar_width, 
                              color="#00ff7f", alpha=0.8, label="Handelsvolumen")  # Helles Grün
            
            self.ax_volume.set_title("Handelsvolumen (Liquidität)", fontsize=11, fontweight='bold', color='#ffffff')
            self.ax_volume.set_ylabel("Volumen", fontsize=10, color='#ffffff')
            
            # 3. Spread (Linie) - Rot/Pink für Spread
            if any(sp > 0 for sp in spread_percentage):
                self.ax_spread.plot(timestamps, spread_percentage, marker="^", linestyle="-", 
                                   color="#ff6b6b", linewidth=2, markersize=3, label="Spread %")  # Helles Rot
                self.ax_spread.set_ylabel("Spread (%)", fontsize=10, color='#ffffff')
            else:
                self.ax_spread.plot(timestamps, spread_absolute, marker="^", linestyle="-", 
                                   color="#ff6b6b", linewidth=2, markersize=3, label="Spread (€)")  # Helles Rot
                self.ax_spread.set_ylabel("Spread (€)", fontsize=10, color='#ffffff')
            
            self.ax_spread.set_title("Bid-Ask Spread", fontsize=11, fontweight='bold', color='#ffffff')
            self.ax_spread.set_xlabel("Zeit", fontsize=10, color='#ffffff')
            
            # Datumsformatierung für alle Plots
            for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.tick_params(axis='x', rotation=45, colors='#ffffff')
                ax.tick_params(axis='y', colors='#ffffff')
            
            # Layout optimieren
            self.fig.tight_layout()
            
        except Exception as e:
            self._show_error_message(skin_name, str(e))
        
        finally:
            self.draw()

    def plot(self, data: List[Tuple[str, float]], skin_name: str):
        """
        Zeichnet nur den Preisverlauf (für Rückwärtskompatibilität).
        
        Args:
            data: Liste von (timestamp, price) Tupeln
            skin_name: Name des Skins für den Titel
        """
        # Alle Subplots leeren und dunkles Theme anwenden
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
        self._apply_dark_theme()
        
        if not data:
            self._show_no_data_message(skin_name)
            return

        try:
            # Nur Preisverlauf im ersten Subplot
            timestamps = [datetime.fromisoformat(ts) for ts, _ in data]
            prices = [p for _, p in data]
            
            self.ax_price.plot(timestamps, prices, marker="o", linestyle="-", 
                              color="#00bfff", linewidth=2, markersize=4)  # Cyan-Blau
            self.ax_price.set_title(f"Preisverlauf: {skin_name}", fontsize=12, fontweight='bold', color='#ffffff')
            self.ax_price.set_ylabel("Preis (€)", fontsize=10, color='#ffffff')
            
            # Andere Subplots als leer markieren
            self.ax_volume.text(0.5, 0.5, 'Keine Volumendaten verfügbar', 
                               ha='center', va='center', transform=self.ax_volume.transAxes, 
                               fontsize=10, alpha=0.7, color='#cccccc')
            self.ax_volume.set_title("Handelsvolumen (Liquidität)", fontsize=11, fontweight='bold', color='#ffffff')
            
            self.ax_spread.text(0.5, 0.5, 'Keine Spread-Daten verfügbar', 
                               ha='center', va='center', transform=self.ax_spread.transAxes, 
                               fontsize=10, alpha=0.7, color='#cccccc')
            self.ax_spread.set_title("Bid-Ask Spread", fontsize=11, fontweight='bold', color='#ffffff')
            self.ax_spread.set_xlabel("Zeit", fontsize=10, color='#ffffff')
            
            # Datumsformatierung
            for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.tick_params(axis='x', rotation=45, colors='#ffffff', labelsize=8)
                ax.tick_params(axis='y', colors='#ffffff', labelsize=8)
            
            self.fig.tight_layout()
            
        except Exception as e:
            self._show_error_message(skin_name, str(e))
        
        finally:
            self.draw()

    def _show_no_data_message(self, skin_name: str):
        """Zeigt eine Nachricht an, wenn keine Daten verfügbar sind."""
        message = f"Keine Daten für: {skin_name}" if skin_name else "Keine Daten verfügbar"
        
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], 
                            ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]):
            ax.text(0.5, 0.5, message, ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12, alpha=0.7, color='#cccccc')
            ax.set_title(title, fontsize=11, fontweight='bold', color='#ffffff')
        
        self.ax_spread.set_xlabel("Zeit", fontsize=10, color='#ffffff')
        self.draw()

    def _show_error_message(self, skin_name: str, error: str):
        """Zeigt eine Fehlermeldung an."""
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], 
                            ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]):
            ax.text(0.5, 0.5, f'Fehler: {error}', ha='center', va='center',
                   transform=ax.transAxes, fontsize=10, color='#ff6b6b')  # Helles Rot für Fehler
            ax.set_title(f"Fehler bei {title}: {skin_name}", fontsize=11, color='#ffffff')
        
        print(f"Fehler beim Plotten: {error}")
        self.draw()

# Alias für Rückwärtskompatibilität
PricePlotCanvas = EnhancedPricePlotCanvas
