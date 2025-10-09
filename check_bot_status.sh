#!/bin/bash
# Script pour vérifier l'état du bot sur le serveur

echo "=== Vérification de l'état du bot ==="
echo

# Vérifier si le bot tourne
echo "1. Vérification des processus Python..."
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "   ✅ Bot en cours d'exécution"
    pgrep -f "python.*bot.py" | while read pid; do
        echo "   PID: $pid"
    done
else
    echo "   ❌ Aucun processus bot.py trouvé"
fi

echo

# Vérifier les fichiers
echo "2. Vérification des fichiers..."
if [ -f "bot.py" ]; then
    echo "   ✅ bot.py trouvé"
else
    echo "   ❌ bot.py introuvable"
fi

if [ -f "cogs/download.py" ]; then
    echo "   ✅ cogs/download.py trouvé"
else
    echo "   ❌ cogs/download.py introuvable"
fi

echo

# Vérifier les logs
echo "3. Vérification des logs..."
if [ -f "bot.log" ]; then
    echo "   ✅ Logs trouvés"
    echo "   📋 Dernières lignes des logs:"
    tail -10 bot.log
else
    echo "   ❌ Aucun fichier de logs trouvé"
fi

echo

# Vérifier les variables d'environnement
echo "4. Vérification des variables d'environnement..."
if [ -f ".env" ]; then
    echo "   ✅ Fichier .env trouvé"
    if grep -q "DISCORD_TOKEN" .env; then
        echo "   ✅ DISCORD_TOKEN configuré"
    else
        echo "   ❌ DISCORD_TOKEN manquant"
    fi
else
    echo "   ❌ Fichier .env introuvable"
fi

echo

# Recommandations
echo "5. Recommandations:"
if ! pgrep -f "python.*bot.py" > /dev/null; then
    echo "   🔄 Redémarrer le bot: python3 bot.py"
    echo "   📋 Vérifier les logs: tail -f bot.log"
else
    echo "   ✅ Bot en cours d'exécution"
    echo "   🔄 Si les commandes ne marchent pas, redémarrer: pkill -f python && python3 bot.py"
fi
