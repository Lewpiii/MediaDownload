# Configuration Top.gg Vote System

## 📋 Vue d'ensemble

Le bot nécessite maintenant que les utilisateurs votent sur top.gg pour accéder à la commande `/download`. Cette fonctionnalité encourage le soutien de la communauté et aide à promouvoir le bot.

## 🔑 Configuration

### 1. Obtenir votre Token Top.gg

1. Allez sur https://top.gg/bot/VOTRE_BOT_ID
2. Cliquez sur **"Edit Bot"**
3. Allez dans la section **"Webhooks"**
4. Copiez votre **Authorization Token**

### 2. Configurer la Variable d'Environnement

Ajoutez cette ligne à votre fichier `.env` :

```env
TOP_GG_TOKEN=votre_token_topgg_ici
```

Ou sur GitHub Secrets :
- Nom : `TOP_GG_TOKEN`
- Valeur : Votre token top.gg

### 3. Configuration du Bot sur Top.gg

1. Assurez-vous que votre bot est listé sur https://top.gg
2. Activez les webhooks dans les paramètres du bot
3. Configurez l'URL du webhook (optionnel, pour les statistiques avancées)

## 🎯 Fonctionnement

### Pour les Utilisateurs

Quand un utilisateur essaie d'utiliser `/download` sans avoir voté :

1. **Un embed apparaît** expliquant qu'un vote est requis
2. **Un bouton "Voter sur top.gg"** est affiché
3. L'utilisateur clique et vote (gratuit, 30 secondes)
4. Il peut ensuite utiliser la commande pendant **12 heures**

### Pour les Développeurs

Le système vérifie automatiquement :
- ✅ Si l'utilisateur a voté dans les 12 dernières heures
- ✅ Gère les erreurs d'API gracieusement
- ✅ Fonctionne même si le token n'est pas configuré (mode ouvert)

## 🛠️ Personnalisation

### Désactiver la Vérification de Vote

Si vous voulez désactiver temporairement la vérification de vote :

1. Retirez `TOP_GG_TOKEN` de votre `.env`
2. Ou commentez `@require_vote()` dans `cogs/download.py`

```python
# @require_vote()  # Commenté = pas de vérification
async def download_media(self, interaction: discord.Interaction):
    ...
```

### Appliquer à d'Autres Commandes

Pour ajouter la vérification de vote à d'autres commandes :

```python
from utils.topgg_checker import require_vote

@app_commands.command()
@require_vote()
async def ma_commande(self, interaction: discord.Interaction):
    # Votre code ici
    ...
```

## 📊 Vérification Manuelle

Pour vérifier si un utilisateur a voté :

```python
# Dans votre code
checker = interaction.client.topgg_checker
has_voted = await checker.has_voted(user_id)
```

## ⚠️ Limitations

- **Durée du vote** : 12 heures (imposé par top.gg)
- **Rate limits** : L'API top.gg a des limites de requêtes
- **Délai** : Il peut y avoir un petit délai entre le vote et la mise à jour

## 🔧 Dépannage

### Le vote ne fonctionne pas ?

1. ✅ Vérifiez que `TOP_GG_TOKEN` est correct
2. ✅ Vérifiez que votre bot est bien listé sur top.gg
3. ✅ Attendez 1-2 minutes après le vote
4. ✅ Vérifiez les logs du bot pour les erreurs API

### Erreur "TOP_GG_TOKEN not configured"

C'est juste un avertissement. Le bot fonctionne en mode ouvert (pas de vérification de vote) si le token n'est pas configuré.

## 📝 Exemple de Message de Vote

```
🗳️ Vote requis !

Pour utiliser cette commande, vous devez d'abord voter pour le bot sur top.gg.

C'est gratuit et ne prend que quelques secondes !
Votre vote nous aide énormément à faire connaître le bot. 💙

[🗳️ Voter sur top.gg]
```

## 🎁 Avantages du Vote

- ✅ Accès complet pendant 12 heures
- ✅ Soutien au développement du bot
- ✅ Aide à faire connaître le bot
- ✅ Amélioration continue des fonctionnalités

## 🔗 Liens Utiles

- **Top.gg Bot Page** : https://top.gg/bot/VOTRE_BOT_ID
- **Documentation API** : https://docs.top.gg/
- **Support Discord** : https://discord.gg/topgg

