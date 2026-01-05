# 🖥️ Configuration Bot sur Serveur

## 🎯 Problème Identifié

Votre bot est hébergé sur un serveur mais les variables d'environnement ne sont pas configurées correctement.

## 🚀 Solutions par Plateforme

### **Heroku**
```bash
# Via CLI Heroku
heroku config:set DISCORD_TOKEN=your_bot_token_here
heroku config:set TOP_GG_TOKEN=your_topgg_token_here

# Ou via l'interface web Heroku
# Settings → Config Vars → Add
```

### **Railway**
1. Allez dans votre projet Railway
2. Cliquez sur "Variables"
3. Ajoutez :
   - `DISCORD_TOKEN` = `your_bot_token_here`
   - `TOP_GG_TOKEN` = `your_topgg_token_here`

### **DigitalOcean App Platform**
1. Allez dans votre app
2. Settings → Environment Variables
3. Ajoutez les variables requises

### **AWS/GCP/Azure**
```bash
# Via CLI ou interface web
# Ajoutez les variables d'environnement dans votre service
```

### **VPS/Serveur Dédié**
```bash
# Méthode 1: Variables système
export DISCORD_TOKEN="your_bot_token_here"
export TOP_GG_TOKEN="your_topgg_token_here"

# Méthode 2: Fichier .env (si supporté)
echo "DISCORD_TOKEN=your_bot_token_here" > .env
echo "TOP_GG_TOKEN=your_topgg_token_here" >> .env

# Méthode 3: Dans votre script de démarrage
# Ajoutez les export dans votre script de démarrage
```

### **Docker**
```bash
# Docker run
docker run -e DISCORD_TOKEN=your_bot_token_here -e TOP_GG_TOKEN=your_topgg_token_here your_image

# Docker Compose
# Dans docker-compose.yml:
environment:
  - DISCORD_TOKEN=your_bot_token_here
  - TOP_GG_TOKEN=your_topgg_token_here
```

## 🔍 Vérification

### 1. **Test sur le Serveur**
```bash
# Uploadez check_server_env.py sur votre serveur
python check_server_env.py
```

### 2. **Vérification des Logs**
Regardez les logs de votre bot pour voir :
- Si le token est détecté
- Si la connexion Discord réussit
- Les erreurs spécifiques

### 3. **Redémarrage**
Après avoir configuré les variables :
```bash
# Redémarrez votre bot/service
# La méthode dépend de votre plateforme
```

## 📋 Checklist

- [ ] Variables d'environnement configurées sur le serveur
- [ ] Bot redémarré après configuration
- [ ] Logs vérifiés pour erreurs
- [ ] Test de la commande `/download`
- [ ] Vérification du système de vote

## 🆘 Support par Plateforme

### **Heroku**
- Documentation : https://devcenter.heroku.com/articles/config-vars
- CLI : `heroku config`

### **Railway**
- Documentation : https://docs.railway.app/deploy/environment-variables
- Interface web dans votre projet

### **DigitalOcean**
- Documentation : https://docs.digitalocean.com/products/app-platform/how-to/use-environment-variables/

### **Docker**
- Documentation : https://docs.docker.com/compose/environment-variables/

---

**Une fois les variables configurées sur votre serveur, le bot fonctionnera parfaitement ! 🎉**
