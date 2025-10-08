# 🚀 Configuration Rapide GitHub Secrets

## 📋 Étapes Rapides

### 1. **Aller sur GitHub**
- Ouvrez votre repository
- Cliquez sur **Settings** (en haut à droite)

### 2. **Accéder aux Secrets**
- Menu gauche : **Secrets and variables**
- Cliquez sur **Actions**

### 3. **Ajouter les Secrets**

#### 🔑 DISCORD_TOKEN
```
Name: DISCORD_TOKEN
Secret: votre_token_discord_du_bot
```

#### 🗳️ TOP_GG_TOKEN (pour le vote)
```
Name: TOP_GG_TOKEN
Secret: votre_token_topgg_api
```

**Comment obtenir TOP_GG_TOKEN :**
1. Allez sur https://top.gg/bot/VOTRE_BOT_ID
2. Cliquez **"Edit Bot"**
3. Section **"Webhooks"**
4. Copiez votre **Authorization token**

### 4. **Variables Optionnelles**
```
LOGS_CHANNEL_ID: 123456789012345678
WEBHOOK_URL: https://discord.com/api/webhooks/...
GOFILE_TOKEN: votre_token_gofile
```

## ✅ Vérification

### Test Local
```bash
# Créer le fichier .env
cp env.example .env
# Éditer .env avec vos vrais tokens
python check_env.py
```

### Test Top.gg API
```bash
python test_topgg.py
```

## 🎯 Résultat

Une fois configuré :
- ✅ Le bot fonctionne normalement
- ✅ Le système de vote Top.gg est actif
- ✅ Les utilisateurs doivent voter pour télécharger
- ✅ Vote valide pendant 12 heures

## 🔒 Sécurité

- ✅ GitHub Secrets = sécurisé pour la production
- ✅ .env = pour le développement local
- ❌ Ne jamais commiter le fichier .env
- ❌ Ne jamais partager vos tokens

## 📞 Problèmes ?

1. **Vote ne fonctionne pas** → Vérifiez TOP_GG_TOKEN
2. **Bot ne démarre pas** → Vérifiez DISCORD_TOKEN  
3. **Erreurs API** → Utilisez `python test_topgg.py`

---

**Commit ID:** `1c318ae` - Tout est prêt ! 🎉
