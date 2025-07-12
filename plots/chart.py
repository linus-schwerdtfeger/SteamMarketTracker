from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Tuple

class PricePlotCanvas(FigureCanvas):
    """Canvas für die Darstellung von Preisverläufen als Matplotlib-Plot."""
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 3))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Plot-Styling
        self.fig.patch.set_facecolor('white')
        self.ax.grid(True, alpha=0.3)

    def plot(self, data: List[Tuple[str, float]], skin_name: str):
        """
        Zeichnet einen Preisverlauf.
        
        Args:
            data: Liste von (timestamp, price) Tupeln
            skin_name: Name des Skins für den Titel
        """
        self.ax.clear()
        
        if not data:
            self.ax.set_title(f"Keine Preisdaten für: {skin_name}" if skin_name else "Keine Preisdaten vorhanden")
            self.ax.text(0.5, 0.5, 'Keine Daten verfügbar', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=self.ax.transAxes, fontsize=12, alpha=0.7)
            self.draw()
            return

        try:
            # Datum-Strings in datetime-Objekte umwandeln
            timestamps = [datetime.fromisoformat(ts) for ts, _ in data]
            prices = [p for _, p in data]
            
            # Plot erstellen
            self.ax.plot(timestamps, prices, marker="o", linestyle="-", 
                        color="blue", linewidth=2, markersize=4)
            
            # Styling
            self.ax.set_title(f"Preisverlauf: {skin_name}", fontsize=12, fontweight='bold')
            self.ax.set_xlabel("Zeit", fontsize=10)
            self.ax.set_ylabel("Preis (€)", fontsize=10)
            self.ax.grid(True, alpha=0.3)
            
            # Rotiere x-Achsen Labels
            self.ax.tick_params(axis='x', rotation=45, labelsize=8)
            self.ax.tick_params(axis='y', labelsize=8)

            # Datumsformat setzen
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
            
            # Automatische Formatierung der Datumsbeschriftung
            self.fig.autofmt_xdate()
            
            # Layout optimieren
            self.fig.tight_layout()
            
        except Exception as e:
            self.ax.set_title(f"Fehler beim Laden der Daten für: {skin_name}")
            self.ax.text(0.5, 0.5, f'Fehler: {str(e)}', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=self.ax.transAxes, fontsize=10, color='red')
            print(f"Fehler beim Plotten: {e}")
        
        finally:
            self.draw()
