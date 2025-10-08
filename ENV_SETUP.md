# 🔐 Configuration des Variables d'Environnement

## 📋 Variables Requises

Voici les variables d'environnement nécessaires pour le bot :

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `DISCORD_TOKEN` | Token du bot Discord | ✅ Oui |
| `TOP_GG_TOKEN` | Token API Top.gg | ❌ Non (mode ouvert si absent) |
| `LOGS_CHANNEL_ID` | ID du canal de logs | ❌ Non |
| `WEBHOOK_URL` | URL du webhook | ❌ Non |
| `GOFILE_TOKEN` | Token GoFile | ❌ Non |

## 🏠 Configuration Locale (.env)

### 1. Créer le fichier .env
```bash
# Copier le fichier d'exemple
cp env.example .env
```

### 2. Éditer le fichier .env
```env
DISCORD_TOKEN=votre_token_discord_ici
TOP_GG_TOKEN=votre_token_topgg_ici
LOGS_CHANNEL_ID=123456789012345678
WEBHOOK_URL=https://discord.com/api/webhooks/...
GOFILE_TOKEN=votre_token_gofile_ici
```

## ☁️ Configuration GitHub Secrets

### 1. Aller sur GitHub
- Ouvrez votre repository sur GitHub
- Cliquez sur **Settings** (en haut à droite)

### 2. Accéder aux Secrets
- Dans le menu de gauche, cliquez sur **Secrets and variables**
- Cliquez sur **Actions**

### 3. Ajouter les Secrets
Cliquez sur **New repository secret** et ajoutez :

#### 🔑 DISCORD_TOKEN
- **Name**: `DISCORD_TOKEN`
- **Secret**: Votre token Discord du bot

#### 🗳️ TOP_GG_TOKEN
- **Name**: `TOP_GG_TOKEN`
- **Secret**: Votre token Top.gg

**Comment obtenir le token Top.gg :**
1. Allez sur https://top.gg/bot/VOTRE_BOT_ID
2. Cliquez sur **"Edit Bot"**
3. Allez dans la section **"Webhooks"**
4. Copiez votre **Authorization token**

#### 📝 Autres variables (optionnelles)
- `LOGS_CHANNEL_ID`: ID du canal Discord pour les logs
- `WEBHOOK_URL`: URL du webhook Discord
- `GOFILE_TOKEN`: Token pour GoFile

## 🧪 Test de Configuration

### Vérifier les variables localement
```bash
python check_env.py
```

### Vérifier sur GitHub
- Les secrets sont automatiquement disponibles dans GitHub Actions
- Vérifiez les logs de déploiement pour voir si les variables sont chargées

## 🔒 Sécurité

### ✅ Bonnes pratiques
- ✅ Utilisez GitHub Secrets pour la production
- ✅ Utilisez .env pour le développement local
- ✅ Ne commitez JAMAIS le fichier .env
- ✅ Utilisez des tokens avec des permissions minimales

### ❌ À éviter
- ❌ Ne jamais mettre de tokens dans le code
- ❌ Ne jamais commiter le fichier .env
- ❌ Ne jamais partager vos tokens

## 🚀 Déploiement

### GitHub Actions
Les variables sont automatiquement disponibles dans vos workflows :

```yaml
- name: Run Bot
  env:
    DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}
    TOP_GG_TOKEN: ${{ secrets.TOP_GG_TOKEN }}
  run: python bot.py
```

### VPS/Serveur
```bash
# Exporter les variables
export DISCORD_TOKEN="votre_token"
export TOP_GG_TOKEN="votre_token"

# Ou utiliser un fichier .env
python bot.py
```

## 🔍 Dépannage

### Variables non trouvées
```bash
# Vérifier les variables
python check_env.py

# Vérifier dans le code
import os
print(os.getenv('TOP_GG_TOKEN'))
```

### Token Top.gg invalide
- Vérifiez que le token est correct
- Vérifiez que le bot est bien listé sur top.gg
- Vérifiez les permissions du token

### Mode ouvert
Si `TOP_GG_TOKEN` n'est pas configuré, le bot fonctionne en mode ouvert (pas de vérification de vote).

## 📞 Support

Si vous avez des problèmes :
1. Vérifiez que tous les secrets sont bien configurés
2. Vérifiez les logs du bot
3. Testez avec `python check_env.py`
4. Vérifiez la documentation Top.gg
