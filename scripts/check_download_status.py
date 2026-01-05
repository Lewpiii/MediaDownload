#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'état des téléchargements
"""

import os
import sys
import time
from pathlib import Path
from config import DOWNLOAD_CONFIG

def check_download_status():
    """Vérifier l'état des téléchargements"""
    print("🔍 Diagnostic des téléchargements...")
    print("=" * 50)
    
    temp_dir = DOWNLOAD_CONFIG['temp_dir']
    
    # Vérifier le dossier temporaire
    if not os.path.exists(temp_dir):
        print(f"❌ Dossier temporaire introuvable: {temp_dir}")
        return False
    
    print(f"✅ Dossier temporaire trouvé: {temp_dir}")
    
    # Lister les fichiers
    files = []
    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_time = os.path.getmtime(file_path)
                files.append({
                    'name': filename,
                    'size': file_size,
                    'time': file_time,
                    'path': file_path
                })
    except PermissionError:
        print("❌ Permission refusée pour accéder au dossier")
        return False
    
    if not files:
        print("✅ Aucun fichier partiel trouvé - système propre")
        return True
    
    print(f"⚠️  {len(files)} fichiers partiels trouvés:")
    print("-" * 30)
    
    total_size = 0
    for file_info in files:
        size_mb = file_info['size'] / (1024 * 1024)
        total_size += file_info['size']
        age_minutes = (time.time() - file_info['time']) / 60
        
        status = "🟢" if age_minutes < 5 else "🟡" if age_minutes < 30 else "🔴"
        print(f"{status} {file_info['name']} ({size_mb:.1f}MB) - {age_minutes:.0f}min")
    
    print("-" * 30)
    print(f"📊 Total: {len(files)} fichiers, {total_size / (1024*1024):.1f}MB")
    
    # Recommandations
    print("\n💡 Recommandations:")
    if total_size > 100 * 1024 * 1024:  # Plus de 100MB
        print("• Utilisez /recover-download pour nettoyer")
        print("• Les fichiers partiels occupent beaucoup d'espace")
    elif len(files) > 10:
        print("• Nombreux fichiers partiels détectés")
        print("• Considérez un nettoyage avec /recover-download")
    else:
        print("• Situation acceptable")
        print("• Vous pouvez continuer les téléchargements")
    
    return True

def main():
    """Fonction principale"""
    try:
        success = check_download_status()
        if success:
            print("\n✅ Diagnostic terminé avec succès")
            sys.exit(0)
        else:
            print("\n❌ Diagnostic échoué")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Diagnostic interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
