#!/bin/bash
echo "--- Démarrage de la procédure de sauvegarde ---"

# A. Génération des dépendances
echo "1. Génération requirements.txt..."
pip freeze > requirements.txt

# B. Création du contexte IA
echo "2. Rédaction du CONTEXTE_IA.md..."
cat << 'EOF' > CONTEXTE_IA.md
# 📁 PRISM V9.7 - DOCUMENT DE TRANSMISSION

## 🎯 Objectif
Outil d'analyse acoustique expert pour détecter les nuisances de PAC (Pompes à Chaleur) via des fichiers ONYX (.csv).
Approche : Semi-automatique. L'IA détecte, l'expert humain valide/corrige via l'interface graphique.

## 🛠 État Technique (V9.7 Stable)
- **Framework :** PyQt5 + PyQtGraph (Performance requise pour zoom temps réel).
- **Fonctions Actives :**
    - Navigation Clavier (Espace, Flèches).
    - **Visualisation Marqueurs ONYX :** Badges haute visibilité (Noir sur couleur) en haut du graphe.
    - **Interactivité :** Clic gauche sur un badge = Menu contextuel (Modifier/Supprimer).
    - **Analyse Spectrale :** Moyenne glissante 5s + Instantané.

## ⚠️ Points Critiques (NE PAS TOUCHER SANS COMPRENDRE)
1. **Affichage Badges :** Utiliser `pg.TextItem` avec style natif (`fill`, `color`). Ne JAMAIS réintroduire de HTML/CSS dans les objets graphiques (cause de crashs V9.6).
2. **Format ONYX :** Les CSV ont un entête double (`header=1`) et encodage `utf-8-sig`.
3. **Synchronisation :** Le player audio est esclave du timestamp global.

## 🚀 Prochaine Étape
- Sauvegarder les modifications faites par l'utilisateur (les marqueurs corrigés) dans un fichier persistant (`ia_knowledge.csv`) pour entraîner le futur algorithme de détection.
EOF

# C. Création de l'architecture
echo "3. Rédaction de ARCHITECTURE.md..."
cat << 'EOF' > ARCHITECTURE.md
# 🏗 ARCHITECTURE DU PROJET

## Structure
- `/ui/dashboard.py` : Interface principale (V9.7). Contient la boucle d'événements et la gestion graphique.
- `/ai_brain/ia_core.py` : Moteur de calcul acoustique (Norme NF S 31-010).
- `/utils/` : Gestion des logs.

## Choix Techniques
- **Graphiques :** PyQtGraph est utilisé au lieu de Matplotlib pour la fluidité.
- **Audio :** QtMultimedia gère la lecture sans bloquer l'interface.
EOF

# D. Compression ZIP
echo "4. Création de l'archive ZIP..."
zip -r PRISM_V9.7_TRANSMISSION.zip . -x "venv/*" -x "__pycache__/*" -x "*.DS_Store" -x "*.git/*" -x "backups/*" -x "make_backup.sh"

echo "✅ SUCCÈS : Archive 'PRISM_V9.7_TRANSMISSION.zip' créée."
