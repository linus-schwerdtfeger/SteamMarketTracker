from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Tuple
import numpy as np

class MarketDataCanvas(FigureCanvas):
    """Canvas für umfassende Marktdatenvisualisierung (Preis, Volumen, Spread)."""
    
    def __init__(self, parent=None):
        # Optimierte Figure-Größe für drei Subplots
        self.fig = Figure(figsize=(12, 8), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Dunkler Hintergrund
        self.fig.patch.set_facecolor('#2d2d2d')
        
        # Drei optimierte Subplots
        self.ax_price = self.fig.add_subplot(3, 1, 1)
        self.ax_volume = self.fig.add_subplot(3, 1, 2)
        self.ax_spread = self.fig.add_subplot(3, 1, 3)
        
        self._apply_dark_theme()
        # Reduzierte hspace für kompakteres Layout
        self.fig.subplots_adjust(hspace=0.25, left=0.08, right=0.96, top=0.94, bottom=0.10)

    def _apply_dark_theme(self):
        """Wendet optimiertes dunkles Design an."""
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.set_facecolor('#2d2d2d')
            ax.grid(True, alpha=0.3, color='#cccccc', linestyle='-', linewidth=0.6)
            
            for spine in ax.spines.values():
                spine.set_color('#cccccc')
                spine.set_linewidth(0.8)
            
            ax.tick_params(axis='both', colors='#ffffff', labelsize=9, width=0.8)
            ax.title.set_color('#ffffff')
            ax.xaxis.label.set_color('#ffffff')
            ax.yaxis.label.set_color('#ffffff')

    def plot_market_data(self, data: List[Tuple], skin_name: str):
        """
        Zeichnet umfassende Marktdaten.
        
        Args:
            data: Liste von (timestamp, price, median_price, volume, spread_absolute, spread_percentage) Tupeln
            skin_name: Name des Skins
        """
        # Plots zurücksetzen
        for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
            ax.clear()
        self._apply_dark_theme()
        
        if not data:
            self._show_no_data_message(skin_name)
            return

        try:
            # Effiziente Datenextraktion mit NumPy
            timestamps = [datetime.fromisoformat(row[0]) for row in data]
            prices = np.array([row[1] for row in data])
            median_prices = np.array([row[2] for row in data])
            volumes = np.array([row[3] for row in data])
            spread_absolute = np.array([row[4] for row in data])
            spread_percentage = np.array([row[5] for row in data])
            
            # 1. Preisverlauf
            self.ax_price.plot(timestamps, prices, 
                              color="#00bfff", linewidth=2.5, marker="o", markersize=4,
                              label="Niedrigster Preis", alpha=0.9)
            
            # Median-Preis nur wenn verfügbar
            median_plotted = False
            if np.any(median_prices > 0):
                self.ax_price.plot(timestamps, median_prices, 
                                  color="#ffa500", linewidth=2, linestyle="--", 
                                  marker="s", markersize=3, label="Median Preis", alpha=0.8)
                median_plotted = True
                
                legend = self.ax_price.legend(loc='upper left', fontsize=9, framealpha=0.9)
                legend.get_frame().set_facecolor('#2d2d2d')
                legend.get_frame().set_edgecolor('#cccccc')
                for text in legend.get_texts():
                    text.set_color('#ffffff')
            
            self.ax_price.set_title(f"Preisverlauf: {skin_name}", fontsize=13, fontweight='bold')
            self.ax_price.set_ylabel("Preis (€)", fontsize=11)
            
            # Y-Achse optimieren - KORRIGIERT für beide Preistypen
            if len(prices) > 1:
                # Sammle alle relevanten Preise
                all_prices = list(prices)
                
                # Füge gültige Median-Preise hinzu
                if median_plotted:
                    valid_median = median_prices[median_prices > 0]
                    all_prices.extend(valid_median)
                
                # Setze Y-Achse basierend auf ALLEN Preisen
                if all_prices:
                    min_price = min(all_prices)
                    max_price = max(all_prices)
                    price_range = max_price - min_price
                    
                    # Intelligente Margin-Berechnung
                    if price_range > 0:
                        margin = price_range * 0.05  # 5% Margin
                    else:
                        margin = max_price * 0.1 if max_price > 0 else 1.0  # 10% bei gleichen Preisen
                    
                    # Mindest-Margin für sehr kleine Spreads
                    margin = max(margin, 0.1)
                    
                    self.ax_price.set_ylim(min_price - margin, max_price + margin)
                    
                    # Debug-Info (optional)
                    print(f"Price range: {min_price:.2f}€ - {max_price:.2f}€ (Range: {price_range:.2f}€)")
            
            # 2. Handelsvolumen
            if len(timestamps) > 1:
                time_delta = (timestamps[-1] - timestamps[0]).total_seconds() / len(timestamps)
                bar_width = time_delta / 86400 * 0.8
            else:
                bar_width = 0.8
                
            self.ax_volume.bar(timestamps, volumes, width=bar_width, 
                              color="#00ff7f", alpha=0.8, edgecolor='#cccccc', linewidth=0.5)
            
            self.ax_volume.set_title("Handelsvolumen (Liquidität)", fontsize=12, fontweight='bold')
            self.ax_volume.set_ylabel("Anzahl Transaktionen", fontsize=11)
            
            # Volume-Statistik
            if len(volumes) > 0:
                avg_volume = np.mean(volumes)
                max_volume = np.max(volumes)
                self.ax_volume.text(0.02, 0.95, f'Ø: {avg_volume:.0f} | Max: {max_volume:.0f}', 
                                   transform=self.ax_volume.transAxes, fontsize=9, 
                                   color='#ffffff', bbox=dict(boxstyle="round,pad=0.3", 
                                   facecolor='#2d2d2d', alpha=0.8))
            
            # 3. Spread - Intelligente Auswahl
            use_percentage = np.any(spread_percentage > 0) and np.mean(spread_percentage) < 50
            
            if use_percentage:
                spread_data = spread_percentage
                ylabel = "Spread (%)"
                color = "#ff6b6b"
                unit = "%"
            else:
                spread_data = spread_absolute
                ylabel = "Spread (€)"
                color = "#ff9500"
                unit = "€"
            
            self.ax_spread.plot(timestamps, spread_data, 
                               color=color, linewidth=2.5, marker="^", markersize=4,
                               alpha=0.9)
            
            self.ax_spread.set_title("Bid-Ask Spread (Markt-Effizienz)", fontsize=12, fontweight='bold')
            self.ax_spread.set_ylabel(ylabel, fontsize=11)
            self.ax_spread.set_xlabel("Zeit", fontsize=11)
            
            # Spread-Statistik
            if len(spread_data) > 0:
                avg_spread = np.mean(spread_data)
                min_spread = np.min(spread_data)
                self.ax_spread.text(0.02, 0.95, f'Ø: {avg_spread:.1f}{unit} | Min: {min_spread:.1f}{unit}', 
                                   transform=self.ax_spread.transAxes, fontsize=9, 
                                   color='#ffffff', bbox=dict(boxstyle="round,pad=0.3", 
                                   facecolor='#2d2d2d', alpha=0.8))
            
            # Optimierte Datumsformatierung - HORIZONTAL statt schräg
            date_format = '%d.%m' if len(timestamps) > 7 else '%d.%m %H:%M'
            
            # Intelligente Label-Reduktion für bessere Lesbarkeit
            max_labels = 8  # Maximal 8 Labels auf X-Achse
            label_interval = max(1, len(timestamps) // max_labels)
            
            for ax in [self.ax_price, self.ax_volume, self.ax_spread]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
                
                # HORIZONTAL statt rotation=45
                ax.tick_params(axis='x', rotation=0, labelsize=8)
                
                # Adaptive Label-Anzahl basierend auf Datenmenge
                if len(timestamps) > 15:
                    # Bei vielen Datenpunkten: Weniger Labels anzeigen
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps)//max_labels)))
                elif len(timestamps) > 5:
                    # Bei mittlerer Anzahl: Jeden 2. anzeigen
                    for i, label in enumerate(ax.xaxis.get_ticklabels()):
                        if i % 2 != 0:
                            label.set_visible(False)
            
            # Nur das unterste Diagramm zeigt X-Achsen-Labels
            # Die oberen beiden sparen Platz
            self.ax_price.tick_params(axis='x', labelbottom=False)
            self.ax_volume.tick_params(axis='x', labelbottom=False)
            # self.ax_spread behält die Labels (unterstes Diagramm)
            
            self.fig.tight_layout()
            
        except Exception as e:
            self._show_error_message(skin_name, str(e))
        
        finally:
            self.draw()

    def _show_no_data_message(self, skin_name: str):
        """Zeigt Nachricht bei fehlenden Daten."""
        message = f"Keine Marktdaten verfügbar für:\n{skin_name}" if skin_name else "Keine Daten verfügbar"
        
        titles = ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], titles):
            ax.text(0.5, 0.5, message, ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14, color='#cccccc',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='#2d2d2d', alpha=0.8))
            ax.set_title(title, fontsize=12, fontweight='bold')
        
        self.ax_spread.set_xlabel("Zeit", fontsize=11)
        self.draw()

    def _show_error_message(self, skin_name: str, error: str):
        """Zeigt Fehlermeldung."""
        error_msg = f"Fehler beim Laden der Marktdaten:\n{error}"
        
        titles = ["Preisverlauf", "Handelsvolumen", "Bid-Ask Spread"]
        for ax, title in zip([self.ax_price, self.ax_volume, self.ax_spread], titles):
            ax.text(0.5, 0.5, error_msg, ha='center', va='center',
                   transform=ax.transAxes, fontsize=12, color='#ff6b6b',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='#2d2d2d', alpha=0.9))
            ax.set_title(f"Fehler - {title}: {skin_name}", fontsize=12, color='#ff6b6b')
        
        print(f"Chart-Fehler: {error}")
        self.draw()
