import sys
import os
import shutil

# 1. Configuration de l'environnement de test
current_dir = os.getcwd()
sys.path.append(current_dir)

from core.loader import EvidenceLoader

def run_test():
    print("--- DÉBUT DU TEST UNITAIRE : LOADER ---")
    
    # --- A. CRÉATION DES DONNÉES SIMULÉES ---
    # On simule un CSV avec le format exact de tes captures (sep=; et decimal=,)
    # Le Timestamp 1766178003.985 correspond à 22:00:03.985
    csv_content = """ts;h;dBA;dBC;Audio_Ref
1766178003.985;22:00:03;27,9;38,7;2025-12-19_22h00_Audio.flac
1766178006.995;22:00:06;26,6;38,3;2025-12-19_22h00_Audio.flac"""
    
    test_csv_name = "test_project.csv"
    test_audio_name = "2025-12-19_22h00_Audio.flac"
    
    print(f"[1] Création du fichier CSV temporaire : {test_csv_name}")
    with open(test_csv_name, "w") as f:
        f.write(csv_content)
        
    print(f"[2] Création du fichier Audio temporaire (Fake) : {test_audio_name}")
    with open(test_audio_name, "w") as f:
        f.write("DATA_AUDIO_FAKE") # Contenu bidon, juste pour que le fichier existe

    # --- B. EXÉCUTION DU LOADER ---
    print("[3] Lancement du chargement...")
    loader = EvidenceLoader()
    success, msg = loader.load_project(test_csv_name)
    
    # --- C. VÉRIFICATION DES RÉSULTATS ---
    print("\n--- RÉSULTAT ---")
    print(msg)
    
    if success:
        # Vérification mathématique du décalage
        # Audio commence à 22:00:00.000
        # CSV commence à 22:00:03.985
        # Décalage attendu = 3.985 secondes
        if abs(loader.time_offset - 3.985) < 0.001:
            print("\n[SUCCÈS] Le calcul de l'offset est EXACT (3.985s).")
        else:
            print(f"\n[ERREUR] Mauvais calcul d'offset : {loader.time_offset}")
    else:
        print("\n[ÉCHEC] Le loader n'a pas réussi à charger le projet.")

    # --- D. NETTOYAGE ---
    # On supprime les fichiers de test
    if os.path.exists(test_csv_name): os.remove(test_csv_name)
    if os.path.exists(test_audio_name): os.remove(test_audio_name)
    print("\n[FIN] Nettoyage effectué.")

if __name__ == "__main__":
    run_test()
