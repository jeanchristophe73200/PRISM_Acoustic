import os
import pandas as pd
import numpy as np
from datetime import datetime

class EvidenceLoader:
    def __init__(self):
        self.csv_data = None
        self.audio_path = None
        self.sampling_step = 3.0
        self.start_time_audio = 0.0
        self.time_offset = 0.0

    def load_project(self, csv_path):
        if not os.path.exists(csv_path):
            return False, "Fichier CSV introuvable."

        try:
            # 1. Trouver le header
            header_idx = 0
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i in range(50):
                    line = f.readline()
                    # On cherche 'ts' et 'dBA' même s'ils ont des guillemets
                    if "ts" in line and "dBA" in line:
                        header_idx = i
                        break
            
            # 2. Chargement
            df = pd.read_csv(csv_path, sep=';', header=header_idx, low_memory=False)

            # --- CORRECTION NETTOYAGE NOMS DE COLONNES ---
            # On force le nettoyage des guillemets doubles (") et simples (') et des espaces
            df.columns = [str(c).strip().replace('"', '').replace("'", "") for c in df.columns]
            # ---------------------------------------------

            # Vérification
            required_cols = ['ts', 'dBA', 'Audio_Ref']
            for col in required_cols:
                if col not in df.columns:
                    # Debug info pour comprendre pourquoi ça échoue
                    cols_trouvees = ", ".join(df.columns)
                    return False, f"Format CSV invalide. Colonne '{col}' introuvable.\nColonnes trouvées : {cols_trouvees}"

            # 3. Typage et Nettoyage données
            df['ts'] = pd.to_numeric(df['ts'], errors='coerce')
            if df['dBA'].dtype == object:
                df['dBA'] = df['dBA'].astype(str).str.replace(',', '.').astype(float)
            
            df = df.dropna(subset=['ts', 'dBA'])
            self.csv_data = df

            # 4. Calculs
            if len(df) > 1:
                self.sampling_step = round(float(df['ts'].iloc[1]) - float(df['ts'].iloc[0]), 3)
            
            ref_audio_name = str(df['Audio_Ref'].iloc[0]).strip()
            project_folder = os.path.dirname(csv_path)
            audio_path = os.path.join(project_folder, ref_audio_name)

            if os.path.exists(audio_path):
                self.audio_path = audio_path
                try:
                    # ... (Calcul offset date identique) ...
                    basename = os.path.basename(audio_path)
                    date_part = basename.split('_Audio')[0]
                    dt = datetime.strptime(date_part, "%Y-%m-%d_%Hh%M")
                    self.start_time_audio = dt.timestamp()
                    self.time_offset = float(df['ts'].iloc[0]) - self.start_time_audio
                except: pass
                return True, f"Données et Audio chargés."
            else:
                return True, f"Données chargées. Audio absent."

        except Exception as e:
            return False, f"Erreur critique : {str(e)}"
