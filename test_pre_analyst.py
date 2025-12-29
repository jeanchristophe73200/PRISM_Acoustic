import pandas as pd
from core.pre_analyst import PreAnalyst

def run_test():
    print("--- TEST UNITAIRE : PRE-ANALYSTE ---")
    
    # 1. Création d'un DataFrame simulé (Similaire au Loader)
    # Cas : 
    # - Ligne 1 : Calme (30dB), Vent faible (2.0)
    # - Ligne 2 : Bruit fort (50dB), Vent FORT (8.5 - Dépassement)
    # - Ligne 3 : Calme (32dB), Vent moyen (4.0)
    
    data = {
        'ts': [1000, 1003, 1006],
        'dBA': [30.0, 50.0, 32.0],
        'vent': ["2,0", "8.5", 4.0] # Mélange types pour tester la robustesse
    }
    df = pd.DataFrame(data)
    
    # 2. Analyse
    analyst = PreAnalyst()
    res = analyst.analyze_dataset(df)
    
    # 3. Vérifications
    print("Résultats :")
    print(f"- Min dBA (Attendu 30.0) : {res['min_dba']}")
    print(f"- Suggestion Résiduel (Doit être = Min) : {res['residual_suggestion']}")
    print(f"- Nombre d'alertes vent (Attendu 1) : {len(res['wind_alerts'])}")
    
    if res['min_dba'] == 30.0 and len(res['wind_alerts']) == 1:
        print("\n[SUCCÈS] Le module calcule les stats et détecte la météo.")
    else:
        print("\n[ÉCHEC] Erreur de calcul.")

if __name__ == "__main__":
    run_test()
