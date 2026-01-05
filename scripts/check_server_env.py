#!/usr/bin/env python3
"""
Script de vérification des variables d'environnement sur serveur
"""

import os
import sys

def check_environment():
    """Vérifier les variables d'environnement"""
    print("=== Server Environment Check ===")
    
    # Variables requises
    required_vars = {
        'DISCORD_TOKEN': 'Discord Bot Token',
        'TOP_GG_TOKEN': 'Top.gg API Token (optional)'
    }
    
    # Variables optionnelles
    optional_vars = {
        'LOGS_CHANNEL_ID': 'Logs Channel ID',
        'WEBHOOK_URL': 'Webhook URL',
        'GOFILE_TOKEN': 'GoFile Token'
    }
    
    print("\nRequired Variables:")
    all_good = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Masquer le token pour la sécurité
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✓ {var}: {masked_value} ({description})")
        else:
            print(f"✗ {var}: NOT SET ({description})")
            if var == 'DISCORD_TOKEN':
                all_good = False
    
    print("\nOptional Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: SET ({description})")
        else:
            print(f"- {var}: NOT SET ({description})")
    
    print(f"\n=== Result: {'✓ ALL GOOD' if all_good else '✗ MISSING REQUIRED VARS'} ===")
    
    if not all_good:
        print("\nTo fix:")
        print("1. Set DISCORD_TOKEN environment variable")
        print("2. Restart your bot/application")
        print("3. Check your hosting platform documentation")
    
    return all_good

if __name__ == "__main__":
    check_environment()
