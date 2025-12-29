import logging
import os
import sys

def setup_logger():
    """
    Configure un logger robuste qui écrit dans la console ET dans un fichier.
    """
    log_filename = "prism_debug.log"
    
    # Configuration de base
    logger = logging.getLogger("PRISM_Logger")
    logger.setLevel(logging.DEBUG)
    
    # Eviter les doublons de logs si la fonction est rappelée
    if logger.handlers:
        return logger

    # Format du log : [DATE HEURE] [NIVEAU] Message
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. Handler Fichier (garde tout l'historique)
    file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # 2. Handler Console (pour voir en direct)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    logger.info("--- NOUVELLE SESSION PRISM DÉMARRÉE ---")
    return logger

# Instance globale utilisable partout
log = setup_logger()
