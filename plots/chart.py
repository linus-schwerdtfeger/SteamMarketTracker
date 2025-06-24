from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime

class PricePlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(5, 3))
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot(self, data, skin_name):
        self.ax.clear()
        if not data:
            self.ax.set_title("Keine Preisdaten vorhanden.")
            self.draw()
            return

        # Datum-Strings in datetime-Objekte umwandeln
        timestamps = [datetime.fromisoformat(ts) for ts, _ in data]
        prices = [p for _, p in data]
        self.ax.plot(timestamps, prices, marker="o", linestyle="-", color="blue")
        self.ax.set_title(f"Preisverlauf: {skin_name}")
        self.ax.set_xlabel("Zeit")
        self.ax.set_ylabel("Preis (€)")
        self.ax.grid(True)
        self.ax.tick_params(axis='x', rotation=45)

        # Datumsformat setzen, z.B. Tag.Monat.Jahr
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        self.figure.autofmt_xdate()  # Automatische Formatierung der Datumsbeschriftung

        self.figure.tight_layout()
        self.draw()
