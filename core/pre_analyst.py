import pandas as pd
import numpy as np

class PreAnalyst:
    def __init__(self):
        # Seuils par défaut (seront ajustés par l'opérateur plus tard)
        self.wind_limit_ms = 5.0  # 5 m/s (environ 18 km/h) - Seuil NF S 31-010

    def analyze_dataset(self, df):
        """
        Analyse statistique du DataFrame chargé.
        Retourne un dictionnaire de résultats.
        """
        results = {
            "min_dba": 0.0,
            "max_dba": 0.0,
            "avg_dba": 0.0,
            "l90_dba": 0.0,
            "residual_suggestion": 0.0,
            "wind_alerts": []  # Liste d'index où le vent est trop fort
        }

        if df is None or df.empty:
            return results

        # 1. Analyse Acoustique de base (dBA)
        try:
            # On s'assure que c'est bien du numérique (déjà fait par Loader, mais double sécu)
            series_dba = pd.to_numeric(df['dBA'], errors='coerce').dropna()
            
            if not series_dba.empty:
                results["min_dba"] = float(series_dba.min())
                results["max_dba"] = float(series_dba.max())
                results["avg_dba"] = float(series_dba.mean())
                # Calcul du L90 (Niveau dépassé 90% du temps = 10ème percentile)
                results["l90_dba"] = float(np.percentile(series_dba, 10))
                
                # SUGGESTION AUTOMATIQUE (Ligne Verte)
                # On propose le MINIMUM absolu comme base de départ (plus sûr juridiquement)
                results["residual_suggestion"] = results["min_dba"]
        except Exception as e:
            print(f"[PreAnalyst] Erreur calcul acoustique: {e}")

        # 2. Analyse Météo (Vent)
        # On cherche la colonne vent (peut s'appeler 'vent', 'wind', 'vitesse_vent')
        wind_col = None
        for col in df.columns:
            if 'vent' in col.lower() or 'wind' in col.lower():
                wind_col = col
                break
        
        if wind_col:
            try:
                # Nettoyage format (virgule -> point) si nécessaire
                if df[wind_col].dtype == object:
                    wind_data = df[wind_col].astype(str).str.replace(',', '.').astype(float)
                else:
                    wind_data = pd.to_numeric(df[wind_col], errors='coerce')

                # Détection des dépassements (> 5 m/s)
                # On stocke les Timestamps concernés
                alerts = df.loc[wind_data > self.wind_limit_ms, 'ts']
                results["wind_alerts"] = alerts.tolist()
                
            except Exception as e:
                print(f"[PreAnalyst] Erreur analyse météo: {e}")

        return results
