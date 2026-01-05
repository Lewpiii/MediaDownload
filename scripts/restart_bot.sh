#!/bin/bash
# Script de redémarrage manuel du bot

echo "=== REDEMARRAGE MANUEL DU BOT ==="
echo "Date: $(date)"
echo ""

# Aller dans le répertoire du bot
cd /home/botuser/discord-bot/MediaDownload

# Arrêter tous les processus Python
echo "1. Arrêt des processus existants..."
sudo pkill -f "python.*src.bot" || true
sudo systemctl stop discord-bot || true
sleep 2

# Vérifier que le fichier .env existe
echo "2. Vérification du fichier .env..."
if [ ! -f .env ]; then
    echo "ERREUR: Fichier .env manquant!"
    echo "Création du fichier .env..."
    echo "DISCORD_TOKEN=your_token_here" > .env
    echo "TOP_GG_TOKEN=your_token_here" >> .env
    echo "ATTENTION: Vous devez configurer vos tokens!"
fi

# Activer l'environnement virtuel
echo "3. Activation de l'environnement virtuel..."
source ../venv/bin/activate

# Installer les dépendances
echo "4. Installation des dépendances..."
pip install -r requirements.txt

# Redémarrer le service
echo "5. Redémarrage du service..."
sudo systemctl start discord-bot

# Attendre et vérifier le statut
echo "6. Vérification du statut..."
sleep 5
sudo systemctl status discord-bot --no-pager

# Vérifier les logs
echo "7. Logs récents:"
sudo journalctl -u discord-bot --no-pager -l -n 10

echo ""
echo "=== REDEMARRAGE TERMINE ==="
