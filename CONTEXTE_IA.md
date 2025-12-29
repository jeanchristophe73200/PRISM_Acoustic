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
