#!/bin/bash
# Ce script crée une copie complète du projet (Time Machine)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="_BACKUPS/PRISM_V2.5_SNAPSHOT_$TIMESTAMP.tar.gz"

echo "--- DÉMARRAGE DE LA SÉCURISATION ---"
# Création de l'archive en excluant le dossier de backup lui-même (pour éviter la récursivité)
tar --exclude='_BACKUPS' --exclude='__pycache__' -czf $BACKUP_NAME .

echo "✅ SAUVEGARDE RÉUSSIE : $BACKUP_NAME"
echo "Vous pouvez procéder aux modifications."
