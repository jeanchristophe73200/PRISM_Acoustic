# 🏗 ARCHITECTURE DU PROJET

## Structure
- `/ui/dashboard.py` : Interface principale (V9.7). Contient la boucle d'événements et la gestion graphique.
- `/ai_brain/ia_core.py` : Moteur de calcul acoustique (Norme NF S 31-010).
- `/utils/` : Gestion des logs.

## Choix Techniques
- **Graphiques :** PyQtGraph est utilisé au lieu de Matplotlib pour la fluidité.
- **Audio :** QtMultimedia gère la lecture sans bloquer l'interface.
