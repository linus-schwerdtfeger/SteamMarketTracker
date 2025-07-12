"""
Counter Strike Skin Markt Preis-Tracker

Ein GUI-Tool zum Verfolgen von Counter Strike Skin-Preisen mit Preishistorie,
Diagrammen und Preisalarmen.
"""
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """Hauptfunktion der Anwendung."""
    app = QApplication(sys.argv)
    app.setApplicationName("CS Skin Markt Preis-Tracker")
    app.setApplicationVersion("1.0")
    
    window = MainWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())