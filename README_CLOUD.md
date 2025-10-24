
# Cloud Kit — Royalties Screener (Railway)

## Fichiers
- `app/main.py` : script principal (scan + backtest + PDF + e-mail)
- `config.yaml` : univers et paramètres
- `requirements.txt` : dépendances
- `.env.example` : modèle des variables e-mail (à mettre dans Railway Variables)
- `Procfile` : démarrage en mode "worker" (optionnel)

## Déploiement sur Railway (pas à pas)
1) Crée un compte sur https://railway.app et clique **New Project**.
2) Choisis **Deploy from GitHub** ou **Deploy from Zip**. Si Zip, uploade `cloud_kit.zip`.
3) Une fois le projet créé :
   - Onglet **Variables** → ajoute ces clés/valeurs (copie depuis `.env.example`):
     - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `TO_EMAIL`
   - Onglet **Settings** → **Start Command** : `python -u app/main.py`
4) Clique **Deploy** pour lancer un test. Vérifie les **Logs**.
5) **Planifier l'exécution quotidienne (cron)** : va dans **Schedules / Cron** (Railway)
   - Ajoute une tâche avec cron ex: `0 9 * * *` et **Command** : `python -u app/main.py`
   - (Cela lancera tous les jours à 09:00, heure du projet ; règle le timezone si disponible)
6) Résultats :
   - Les CSV et PDF sont produits dans `app/output` (stockage éphémère). Le PDF est envoyé par e-mail automatiquement.

## Conseils
- Tu peux mettre `lookback_corr_days`, `lookback_beta_days` etc. dans `config.yaml`.
- Évite de mettre des secrets dans `config.yaml`. Utilise toujours les **Variables** Railway pour SMTP.
- Pour une API en temps réel (pour GPT Actions), expose un FastAPI séparé.
