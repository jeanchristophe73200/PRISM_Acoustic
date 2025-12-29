import sys
import math
import numpy as np
import os
import csv
from datetime import datetime

try:
    from sklearn.neighbors import KNeighborsClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

class CerveauIA:
    def __init__(self):
        self.nom = "Cerveau IA V7.5 (Double Résiduel & PAC)"
        self.limite_basses = 200
        self.limite_aigus = 2000
        
        # --- PARAMETRE EXPERT PAC ---
        # On ne garde que ce qui dure plus de 15 minutes (900s)
        self.duree_min_emergence = 900 
        
        self.residuel_jour = None
        self.residuel_nuit = None
        
        self.memory_file = "ai_brain/ia_knowledge.csv"
        self.model = None
        self.is_trained = False
        self.known_data = []
        self.known_labels = []
        self.load_memory()

    def demarrer(self):
        return f"[{self.nom}] : Prêt. Filtre PAC activé (> {self.duree_min_emergence}s)."

    # (Mémoire & ML inchangés...)
    def load_memory(self):
        if not os.path.exists(self.memory_file): return
        try:
            with open(self.memory_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        self.known_labels.append(row[0])
                        self.known_data.append([float(x) for x in row[1:]])
            if self.known_data and ML_AVAILABLE: self.train_model()
        except: pass

    def save_example(self, spectre_dict, label):
        vals = self._extract_features(spectre_dict)
        if not vals: return "Erreur spectre"
        self.known_data.append(vals)
        self.known_labels.append(label)
        try:
            with open(self.memory_file, 'a', newline='') as f:
                csv.writer(f).writerow([label] + vals)
        except: pass
        if ML_AVAILABLE: self.train_model()
        return f"Appris : {label}"

    def train_model(self):
        if not self.known_data: return
        try:
            self.model = KNeighborsClassifier(n_neighbors=1)
            self.model.fit(self.known_data, self.known_labels)
            self.is_trained = True
        except: pass

    def _extract_features(self, spectre_dict):
        if not spectre_dict: return None
        b, m, a = [], [], []
        for f_str, val in spectre_dict.items():
            try:
                freq = float(f_str.lower().replace('hz', '').strip())
                if freq < self.limite_basses: b.append(val)
                elif freq > self.limite_aigus: a.append(val)
                else: m.append(val)
            except: continue
        return [self._somme_energetique(b), self._somme_energetique(m), self._somme_energetique(a)]

    def _somme_energetique(self, valeurs_db):
        if not valeurs_db: return 0
        try:
            puissances = [10**(v/10) for v in valeurs_db]
            return 10 * math.log10(sum(puissances)) if sum(puissances) > 0 else 0
        except: return 0

    def analyser_spectre(self, spectre_dict):
        features = self._extract_features(spectre_dict)
        if not features: return "Spectre vide."
        nb, nm, na = features
        res = f"[B:{nb:.1f}|M:{nm:.1f}|A:{na:.1f}]"
        pred = ""
        if self.is_trained and self.model:
            try:
                p = self.model.predict(np.array([features]))[0]
                pred = f" 👉 IA : {p}"
            except: pass
        if max(nb, nm, na) == nb: return res + " (Basse)" + pred
        if max(nb, nm, na) == na: return res + " (Aiguë)" + pred
        return res + " (Medium)" + pred

    def analyser_signal(self, val):
        # On ne peut pas répondre précisément sans l'heure, donc on reste vague ici
        return f"{val:.1f} dB"

    # --- NOUVEAU CALCUL RESIDUEL V7.5 (Split Jour/Nuit) ---
    def calculer_residuels_jour_nuit(self, timestamps, valeurs):
        vals_jour = []
        vals_nuit = []
        
        for ts, val in zip(timestamps, valeurs):
            if math.isnan(val): continue
            h = datetime.fromtimestamp(ts).hour
            if 7 <= h < 22:
                vals_jour.append(val)
            else:
                vals_nuit.append(val)
        
        # Calcul L90 Jour
        res_j = np.percentile(vals_jour, 10) if vals_jour else 0
        # Calcul L90 Nuit
        res_n = np.percentile(vals_nuit, 10) if vals_nuit else 0
        
        self.residuel_jour = res_j
        self.residuel_nuit = res_n
        
        return res_j, res_n

    def scanner_emergences(self, timestamps, valeurs):
        # 1. Calcul des 2 résiduels
        res_j, res_n = self.calculer_residuels_jour_nuit(timestamps, valeurs)
        
        evenements_valides = []
        bloc_courant = [] 
        
        for ts, val in zip(timestamps, valeurs):
            if math.isnan(val): continue
            
            # 2. Choix du bon seuil
            dt = datetime.fromtimestamp(ts)
            is_jour = (7 <= dt.hour < 22)
            
            if is_jour:
                seuil = res_j + 5
            else:
                seuil = res_n + 3
            
            if val > seuil:
                bloc_courant.append((ts, val, seuil))
            else:
                if bloc_courant:
                    debut = bloc_courant[0][0]
                    fin = bloc_courant[-1][0]
                    duree = fin - debut
                    
                    # 3. FILTRE PAC : > 15 minutes (900s)
                    if duree >= self.duree_min_emergence:
                        evenements_valides.extend(bloc_courant)
                    
                    bloc_courant = []
        
        # Check fin de fichier
        if bloc_courant:
            if (bloc_courant[-1][0] - bloc_courant[0][0]) >= self.duree_min_emergence:
                evenements_valides.extend(bloc_courant)

        return (res_j, res_n), evenements_valides

if __name__ == "__main__":
    ia = CerveauIA()
    print(ia.demarrer())
