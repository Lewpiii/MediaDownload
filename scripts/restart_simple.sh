#!/bin/bash
# Script simple pour redémarrer le bot

echo "=== Redémarrage du Bot Discord ==="
echo

# Arrêter le bot actuel
echo "1. Arrêt du bot actuel..."
pkill -f "python.*bot.py" 2>/dev/null || echo "   Aucun processus bot.py trouvé"
sleep 2

# Vérifier l'arrêt
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "   Forçage de l'arrêt..."
    pkill -9 -f "python.*bot.py" 2>/dev/null
    sleep 1
fi

echo "   ✅ Bot arrêté"
echo

# Démarrer le bot
echo "2. Démarrage du bot..."
nohup python3 bot.py > bot.log 2>&1 &
BOT_PID=$!

echo "   ✅ Bot démarré (PID: $BOT_PID)"
echo "   📋 Logs: tail -f bot.log"
echo

# Attendre et vérifier
sleep 5
if ps -p $BOT_PID > /dev/null; then
    echo "   ✅ Bot en cours d'exécution"
    echo "   🔗 Vérifiez Discord pour les commandes"
else
    echo "   ❌ Bot arrêté prématurément"
    echo "   📋 Derniers logs:"
    tail -20 bot.log
fi

echo
echo "=== Redémarrage terminé ==="
