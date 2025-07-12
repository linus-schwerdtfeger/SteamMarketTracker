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
        
        # Erstelle drei Subplots: Preis, Volume, Spread
        self.ax_price = self.fig.add_subplot(3, 1, 1)  # Preisverlauf
        self.ax_volume = self.fig.add_subplot(3, 1, 2)  # Volumen (Balken)
        self.ax_spread = self.fig.add_subplot(3, 1, 3)  # Spread (Linie)
        
        # Plot-Styling
        self.fig.patch.set_facecolor('white')
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.grid(True, alpha=0.3)
        
        # Bessere Größenanpassung
        self.fig.subplots_adjust(hspace=0.4, left=0.1, right=0.95, top=0.95, bottom=0.1)
        
        # Tight layout für bessere Darstellung
        self.fig.subplots_adjust(hspace=0.3)

    def plot_comprehensive(self, data: List[Tuple], skin_name: str):
        """
        Zeichnet umfassende Marktdaten (Preis, Volumen, Spread).
        
        Args:
            data: Liste von (timestamp, price, median_price, volume, spread_absolute, spread_percentage) Tupeln
            skin_name: Name des Skins für den Titel
        """
        # Alle Subplots leeren
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
            ax.grid(True, alpha=0.3)
        
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
            
            # 1. Preisverlauf (mit Median-Preis)
            self.ax_price.plot(timestamps, prices, marker="o", linestyle="-", 
                              color="blue", linewidth=2, markersize=3, label="Niedrigster Preis")
            if any(mp > 0 for mp in median_prices):
                self.ax_price.plot(timestamps, median_prices, marker="s", linestyle="--", 
                                  color="orange", linewidth=1.5, markersize=2, label="Median Preis")
                self.ax_price.legend(fontsize=8)
            
            self.ax_price.set_title(f"Preisverlauf: {skin_name}", fontsize=12, fontweight='bold')
            self.ax_price.set_ylabel("Preis (€)", fontsize=10)
            self.ax_price.tick_params(axis='both', labelsize=8)
            
            # 2. Handelsvolumen (Balkendiagramm)
            bar_width = (timestamps[-1] - timestamps[0]).total_seconds() / (len(timestamps) * 86400 * 2) if len(timestamps) > 1 else 1
            self.ax_volume.bar(timestamps, volumes, width=bar_width, 
                              color="green", alpha=0.7, label="Handelsvolumen")
            
            self.ax_volume.set_title("Handelsvolumen (Liquidität)", fontsize=11, fontweight='bold')
            self.ax_volume.set_ylabel("Volumen", fontsize=10)
            self.ax_volume.tick_params(axis='both', labelsize=8)
            
            # 3. Spread (Linie)
            if any(sp > 0 for sp in spread_percentage):
                self.ax_spread.plot(timestamps, spread_percentage, marker="^", linestyle="-", 
                                   color="red", linewidth=2, markersize=3, label="Spread %")
                self.ax_spread.set_ylabel("Spread (%)", fontsize=10)
            else:
                self.ax_spread.plot(timestamps, spread_absolute, marker="^", linestyle="-", 
                                   color="red", linewidth=2, markersize=3, label="Spread (€)")
                self.ax_spread.set_ylabel("Spread (€)", fontsize=10)
            
            self.ax_spread.set_title("Bid-Ask Spread", fontsize=11, fontweight='bold')
            self.ax_spread.set_xlabel("Zeit", fontsize=10)
            self.ax_spread.tick_params(axis='both', labelsize=8)
            
            # Datumsformatierung für alle Plots
            for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.tick_params(axis='x', rotation=45)
            
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
        # Alle Subplots leeren
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
            ax.grid(True, alpha=0.3)
        
        if not data:
            self._show_no_data_message(skin_name)
            return

        try:
            # Nur Preisverlauf im ersten Subplot
            timestamps = [datetime.fromisoformat(ts) for ts, _ in data]
            prices = [p for _, p in data]
            
            self.ax_price.plot(timestamps, prices, marker="o", linestyle="-", 
                              color="blue", linewidth=2, markersize=4)
            self.ax_price.set_title(f"Preisverlauf: {skin_name}", fontsize=12, fontweight='bold')
            self.ax_price.set_ylabel("Preis (€)", fontsize=10)
            
            # Andere Subplots als leer markieren
            self.ax_volume.text(0.5, 0.5, 'Keine Volumendaten verfügbar', 
                               ha='center', va='center', transform=self.ax_volume.transAxes, 
                               fontsize=10, alpha=0.7)
            self.ax_volume.set_title("Handelsvolumen (Liquidität)", fontsize=11, fontweight='bold')
            
            self.ax_spread.text(0.5, 0.5, 'Keine Spread-Daten verfügbar', 
                               ha='center', va='center', transform=self.ax_spread.transAxes, 
                               fontsize=10, alpha=0.7)
            self.ax_spread.set_title("Bid-Ask Spread", fontsize=11, fontweight='bold')
            self.ax_spread.set_xlabel("Zeit", fontsize=10)
            
            # Datumsformatierung
            for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.tick_params(axis='x', rotation=45, labelsize=8)
            
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
                   transform=ax.transAxes, fontsize=12, alpha=0.7)
            ax.set_title(title, fontsize=11, fontweight='bold')
        
        self.ax_spread.set_xlabel("Zeit", fontsize=10)
        self.draw()

    def _show_error_message(self, skin_name: str, error: str):
        """Zeigt eine Fehlermeldung an."""
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], 
                            ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]):
            ax.text(0.5, 0.5, f'Fehler: {error}', ha='center', va='center',
                   transform=ax.transAxes, fontsize=10, color='red')
            ax.set_title(f"Fehler bei {title}: {skin_name}", fontsize=11)
        
        print(f"Fehler beim Plotten: {error}")
        self.draw()

# Alias für Rückwärtskompatibilität
PricePlotCanvas = EnhancedPricePlotCanvas
