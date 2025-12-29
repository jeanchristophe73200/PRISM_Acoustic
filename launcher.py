import sys
from PyQt5.QtWidgets import QApplication
from ui.dashboard import Dashboard
from ai_brain.ia_core import CerveauIA

def main():
    app = QApplication(sys.argv)
    
    # 1. Initialisation du Cerveau
    cerveau = CerveauIA()
    
    # 2. Initialisation du Dashboard V9.5
    window = Dashboard(ia_interface=cerveau)
    window.setWindowTitle("PRISM V9.5 - Analyse Acoustique & IA")
    window.resize(1200, 800)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
