from PyQt5.QtWidgets import QMainWindow
from ui.dashboard import Dashboard
from utils.logger import log

class MainWindow(QMainWindow):
    def __init__(self, ia_interface=None):
        super().__init__()
        
        # On garde le cerveau en mémoire
        self.ia = ia_interface
        
        self.setWindowTitle("PRISM V2.6 - Analyse Acoustique & IA")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #2b2b2b;")
        
        try:
            # --- MODIFICATION V2.6 : On donne le cerveau au Dashboard ---
            self.dashboard = Dashboard(ia_interface=self.ia)
            
            self.setCentralWidget(self.dashboard)
            log.info("Dashboard chargé (avec IA connectée).")
        except Exception as e:
            log.critical(f"Erreur lors du chargement du Dashboard: {e}", exc_info=True)

        if self.ia:
            log.info(f"MainWindow : Cerveau '{self.ia.nom}' transmis au Dashboard.")

        log.info("MainWindow V2.6 initialisée.")
