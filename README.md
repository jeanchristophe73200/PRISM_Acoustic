# PRISM V10 (Platform for Rapid Interactive Sound Monitoring)

## 📌 Présentation
PRISM est une solution logicielle experte développée pour les acousticiens. Elle permet de visualiser, écouter et qualifier des données acoustiques massives (synchronisation Leq/Spectres + Audio) pour la constitution de datasets IA.

## 🚀 Fonctionnalités Clés (V10.2 Stable)

### 1. Visualisation & Analyse
- **Double Vue Synchronisée :** Affichage temporel (Leq) et spectral (1/3 octave).
- **Navigation Fluide :** Moteur graphique haute performance (PyQtGraph).
- **Z-Ordering Intelligent :** Les zones de qualification ne masquent jamais la courbe du signal brut.

### 2. Qualification (Dataset IA)
- **Outils Magnétiques :** Les sélections s'alignent automatiquement sur les pas de temps réels.
- **Classes Prédéfinies :**
  - 🔴 **Source +** (Cible principale : PAC, Industrie...)
  - 🟠 **Source Std** (Bruit standard)
  - 🟡 **Source -** (Secondaire)
  - 🟢 **Résiduel** (Bruit de fond / Calme)
  - ⚪ **Autre** (Exclusion / Pollution)

### 3. Architecture & Sécurité
- **Non-destructif :** Travaille sur copie légère (`_PRISM.csv`), originaux préservés.
- **Local First :** Toutes les données restent sur la machine.

## 🛠 Installation

1. Clonez le dépôt :
   git clone git@github.com:jeanchristophe73200/PRISM_Acoustic.git

2. Installez les dépendances :
   pip install -r requirements.txt

3. Lancez PRISM :
   python prism_launcher.py

---
*Développé par Jean-Christophe Finantz - 2025*
