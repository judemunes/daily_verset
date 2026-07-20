# Verset du jour — appli web

Petite appli web qui affiche un verset biblique différent chaque jour,
avec la même base **PostgreSQL** (`verset_du_jour.py`) que la version CLI.

## Base de données (PostgreSQL)

Le projet utilise PostgreSQL (via `psycopg2`). La connexion se configure
avec la variable d'environnement standard `DATABASE_URL`, au format :

```
postgresql://utilisateur:mot_de_passe@hote:5432/nom_de_la_base
```

- En local, sans rien configurer, l'appli essaie de se connecter à
  `postgresql://postgres:postgres@localhost:5432/verset_du_jour` par
  défaut — adapte cette valeur à ton installation locale si besoin, ou
  définis `DATABASE_URL` toi-même.
- Sur Render, Railway ou Fly.io : ajoute un service PostgreSQL géré, la
  plateforme te fournit une `DATABASE_URL` à coller dans les variables
  d'environnement du service web.
- Les tables (`verses`, `history`, `journal`, `subscriptions`, `comments`,
  `reactions`) sont créées automatiquement au démarrage si elles
  n'existent pas encore (voir `init_db()`), et les versets sont importés
  une seule fois, au tout premier lancement.

### Créer la base en local

```bash
# avec PostgreSQL déjà installé et démarré
createdb verset_du_jour
```

## Notifications navigateur (push)

Un bouton « Activer les notifications » sur la page permet à chaque visiteur
de s'abonner. Chaque jour à 08:00 (heure du serveur), le site envoie
automatiquement le verset du jour à tous les abonnés, même si le site est
fermé.

- Heure d'envoi modifiable via la variable d'environnement `PUSH_TIME`
  (ex: `PUSH_TIME=07:30`).
- Une paire de clés VAPID est générée automatiquement au premier lancement
  dans le fichier défini par `VAPID_KEY_PATH` (par défaut `vapid_private.pem`,
  à la racine du projet) — **ne supprime jamais ce fichier après que des
  gens se sont abonnés**, sinon leurs abonnements deviennent invalides. En
  production, définis `VAPID_KEY_PATH` vers un volume persistant (voir
  section Déployer ci-dessous), sinon ce fichier est perdu à chaque
  redéploiement.
- Les notifications ne fonctionnent que sur un site servi en HTTPS (ou en
  local sur `127.0.0.1`/`localhost`, tolérés comme "contexte sécurisé").
  Vérifie donc que ton hébergeur (Render, Railway...) sert bien le site en
  HTTPS — c'est le cas par défaut sur ces deux plateformes.

## Lancer en local

```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/verset_du_jour"
uvicorn server:app --reload
```

Puis ouvrir http://127.0.0.1:8000

Au premier lancement, les tables sont créées automatiquement dans la base
PostgreSQL et remplies avec les versets. La page appelle `/api/verset`,
qui renvoie toujours le même verset pour la journée en cours (nouveau
verset chaque jour, via l'anti-répétition déjà en place).

## Déployer (Render / Railway / Fly.io)

1. Pousser ce dossier sur un dépôt Git.
2. Créer un service PostgreSQL géré sur la plateforme choisie.
3. Créer un service web, langage Python, et y coller la `DATABASE_URL`
   fournie par le service PostgreSQL dans ses variables d'environnement.
4. Build command : `pip install -r requirements.txt`
5. Start command : `uvicorn server:app --host 0.0.0.0 --port $PORT`

Contrairement à l'ancienne version SQLite, les données (commentaires,
réactions, abonnements, historique) persistent désormais entre les
redéploiements et les mises en veille du service, puisqu'elles vivent
dans la base PostgreSQL gérée plutôt que sur le disque éphémère du
service web.

### Rendre la clé VAPID persistante (Railway)

Sans ça, `vapid_private.pem` vit sur le disque éphémère du service : une
nouvelle clé est générée à chaque redéploiement, ce qui invalide tous les
abonnements aux notifications déjà enregistrés par les visiteurs.

1. Sur ton service web (`daily_verset`) → onglet **Settings** → section
   **Volumes** → **+ New Volume**.
2. Monte-le sur un chemin dédié, par exemple `/data` (Railway crée le
   dossier automatiquement).
3. Onglet **Variables** → ajoute `VAPID_KEY_PATH` avec la valeur
   `/data/vapid_private.pem`.
4. Railway redéploie automatiquement : au prochain démarrage, la clé est
   générée une seule fois dans le volume, puis réutilisée à chaque
   redéploiement suivant.

(Fly.io et Render proposent l'équivalent sous le nom "volume"/"persistent
disk" — même principe : monter un volume, pointer `VAPID_KEY_PATH` dedans.)
