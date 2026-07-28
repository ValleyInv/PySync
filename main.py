import sys
import os

# Add project root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow

def main():
    # Enable High DPI Scaling for modern Windows displays
    app = QApplication(sys.argv)
    app.setApplicationName("PySync - Dropbox Packages")
    app.setOrganizationName("Nor Cal Office")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
