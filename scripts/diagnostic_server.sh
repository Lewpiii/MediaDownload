#!/bin/bash
# Script de diagnostic pour le serveur VPS

echo "=== DIAGNOSTIC SERVEUR BOT ==="
echo "Date: $(date)"
echo ""

# Vérifier le répertoire du bot
echo "1. Vérification du répertoire:"
cd /home/botuser/discord-bot/MediaDownload 2>/dev/null && echo "✓ Répertoire trouvé" || echo "✗ Répertoire non trouvé"
pwd
echo ""

# Vérifier le fichier .env
echo "2. Vérification du fichier .env:"
if [ -f .env ]; then
    echo "✓ Fichier .env existe"
    echo "Contenu (masqué):"
    sed 's/=.*/=***/' .env
else
    echo "✗ Fichier .env manquant"
fi
echo ""

# Vérifier les variables d'environnement
echo "3. Variables d'environnement:"
echo "DISCORD_TOKEN: ${DISCORD_TOKEN:+SET}"
echo "TOP_GG_TOKEN: ${TOP_GG_TOKEN:+SET}"
echo ""

# Vérifier le service systemd
echo "4. Statut du service bot:"
sudo systemctl status discord-bot --no-pager -l
echo ""

# Vérifier les logs récents
echo "5. Logs récents du bot:"
sudo journalctl -u discord-bot --no-pager -l -n 20
echo ""

# Vérifier les processus Python
echo "6. Processus Python en cours:"
ps aux | grep python | grep -v grep
echo ""

# Vérifier les permissions
echo "7. Permissions du répertoire:"
ls -la /home/botuser/discord-bot/MediaDownload/
echo ""

echo "=== FIN DU DIAGNOSTIC ==="
