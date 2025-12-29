import sys
import os
import platform
from PyQt5.QtWidgets import QApplication
from utils.logger import log

# --- IMPORT MODULE IA ---
try:
    from ai_brain.ia_core import CerveauIA
    ia_presente = True
except ImportError as e:
    log.warning(f"Attention : Module IA introuvable ({e})")
    ia_presente = False

def system_check():
    """Vérifications système au démarrage."""
    log.info("--- PRISM V2.5 SYSTEM CHECK ---")
    
    os_info = f"{platform.system()} {platform.release()}"
    log.info(f"Système : {os_info}")
    
    backup_path = "/Volumes/MacDD+/PRISM_V5_Backup"
    if os.path.exists(backup_path):
        log.info(f"Disque de sauvegarde détecté : {backup_path}")
    else:
        log.warning(f"Disque de sauvegarde NON détecté.")

    log.info("Bibliothèques critiques chargées.")

def main():
    try:
        system_check()
        
        app = QApplication(sys.argv)
        log.info("Initialisation de l'interface graphique...")
        
        # --- 1. DÉMARRAGE DU CERVEAU ---
        cerveau_actif = None
        if ia_presente:
            cerveau_actif = CerveauIA()
            msg = cerveau_actif.demarrer()
            log.info(f"IA SYSTEM : {msg}")
        else:
            log.warning("IA SYSTEM : Cerveau non connecté.")

        # Import différé
        from ui.main_window import MainWindow
        
        # --- 2. BRANCHEMENT DU CERVEAU A LA FENETRE ---
        # On donne 'cerveau_actif' à la fenêtre lors de sa création
        window = MainWindow(ia_interface=cerveau_actif)
        window.show()
        
        log.info("Interface chargée. PRISM V2.5 est prêt.")
        
        sys.exit(app.exec_())
    
    except Exception as e:
        log.critical(f"ERREUR FATALE AU LANCEMENT : {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
