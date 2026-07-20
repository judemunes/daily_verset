import json
import os
import secrets
from datetime import datetime
import bcrypt
import psycopg2

# Chaîne de connexion PostgreSQL, surchargeable via la variable
# d'environnement DATABASE_URL (standard Railway/Render/Heroku).
DB_FILE = os.environ.get(
    "DATABASE_URL",
    os.environ.get("DB_FILE", "postgresql://postgres:postgres@localhost:5432/verset_du_jour"),
)

# Liste des versets bibliques
VERSES = [
    {"reference": "Jean 3:16", "text": "Car Dieu a tant aimé le monde qu'il a donné son Fils unique, afin que quiconque croit en lui ne périsse point, mais qu'il ait la vie éternelle."},
    {"reference": "Philippiens 4:13", "text": "Je puis tout par celui qui me fortifie."},
    {"reference": "Psaume 23:1", "text": "L'Éternel est mon berger : je ne manquerai de rien."},
    {"reference": "Proverbes 3:5-6", "text": "Confie-toi en l'Éternel de tout ton cœur, et ne t'appuie pas sur ta sagesse ; reconnais-le dans toutes tes voies, et il aplanira tes sentiers."},
    {"reference": "Jérémie 29:11", "text": "Car je connais les projets que j'ai formés sur vous, dit l'Éternel, projets de paix et non de malheur, afin de vous donner un avenir et de l'espérance."},
    {"reference": "Romains 8:28", "text": "Nous savons, du reste, que toutes choses concourent au bien de ceux qui aiment Dieu, de ceux qui sont appelés selon son dessein."},
    {"reference": "Psaume 46:11", "text": "Arrêtez, et sachez que je suis Dieu : je domine sur les nations, je domine sur la terre."},
    {"reference": "Ésaïe 40:31", "text": "Mais ceux qui se confient en l'Éternel renouvellent leur force. Ils prennent le vol comme les aigles ; ils courent, et ne se lassent point, ils marchent, et ne se fatiguent point."},
    {"reference": "Matthieu 11:28", "text": "Venez à moi, vous tous qui êtes fatigués et chargés, et je vous donnerai du repos."},
    {"reference": "Josué 1:9", "text": "Ne t'ai-je pas donné cet ordre : Fortifie-toi et prends courage ? Ne t'effraie point et ne t'épouvante point, car l'Éternel, ton Dieu, est avec toi dans tout ce que tu entreprendras."},
    {"reference": "Psaume 119:105", "text": "Ta parole est une lampe à mes pieds, et une lumière sur mon sentier."},
    {"reference": "1 Corinthiens 13:13", "text": "Maintenant donc ces trois choses demeurent : la foi, l'espérance, la charité ; mais la plus grande de ces choses, c'est la charité."},
    {"reference": "Romains 12:12", "text": "Réjouissez-vous en espérance. Soyez patients dans l'affliction. Persévérez dans la prière."},
    {"reference": "Psaume 34:9", "text": "Sentez et voyez combien l'Éternel est bon ! Heureux l'homme qui cherche en lui son refuge !"},
    {"reference": "Galates 5:22-23", "text": "Mais le fruit de l'Esprit, c'est l'amour, la joie, la paix, la patience, la bonté, la bénignité, la fidélité, la douceur, la tempérance ; la loi n'est pas contre ces choses."},
    {"reference": "Matthieu 5:16", "text": "Que votre lumière luise ainsi devant les hommes, afin qu'ils voient vos bonnes œuvres, et qu'ils glorifient votre Père qui est dans les cieux."},
    {"reference": "Hébreux 11:1", "text": "Or la foi est une ferme assurance des choses qu'on espère, une démonstration de celles qu'on ne voit pas."},
    {"reference": "Psaume 37:4", "text": "Fais de l'Éternel tes délices, et il te donnera ce que ton cœur désire."},
    {"reference": "Colossiens 3:23", "text": "Tout ce que vous faites, faites-le de bon cœur, comme pour le Seigneur et non pour des hommes."},
    {"reference": "Nombres 6:24-26", "text": "Que l'Éternel te bénisse, et qu'il te garde ! Que l'Éternel fasse luire sa face sur toi, et qu'il t'accorde sa grâce ! Que l'Éternel tourne sa face vers toi, et qu'il te donne la paix !"},
    {"reference": "Romains 12:9", "text": "Que votre amour soit vrai. Détestez le mal, attachez-vous au bien."},
    {"reference": "Éphésiens 4:2", "text": "Soyez simples, doux et patients, supportez-vous les uns les autres avec amour."},
    {"reference": "Éphésiens 4:31", "text": "Ne gardez pas dans votre cœur le mal qu'on vous a fait. Ne vous énervez pas, ne vous mettez pas en colère, faites disparaître de chez vous les cris, les insultes, le mal sous toutes ses formes."},
    {"reference": "Proverbes 22:24", "text": "Ne deviens pas l'ami d'un homme coléreux. Ne va pas avec quelqu'un qui se met en colère facilement."}
]


def get_connection(db_path: str) -> "psycopg2.extensions.connection":
    """Établit une connexion à la base de données PostgreSQL."""
    return psycopg2.connect(db_path)


def _column_exists(cur, table: str, column: str) -> bool:
    """Vérifie si une colonne existe déjà dans une table."""
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def init_db(db_path: str) -> None:
    """Crée les tables si besoin et importe VERSES dans la table 'verses'."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        # Table des versets
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verses (
                id SERIAL PRIMARY KEY,
                reference TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        
        # Table d'historique
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                shown_at TEXT NOT NULL
            )
        """)
        
        # Table de journal
        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id SERIAL PRIMARY KEY,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                logged_at TEXT NOT NULL
            )
        """)
        
        # Table des abonnements aux notifications
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                endpoint TEXT NOT NULL UNIQUE,
                subscription_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Table des commentaires
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                pseudo TEXT NOT NULL,
                text TEXT NOT NULL,
                parent_id INTEGER REFERENCES comments(id),
                created_at TEXT NOT NULL,
                edit_token TEXT,
                edited_at TEXT
            )
        """)
        
        # Ajout des colonnes si elles n'existent pas
        if not _column_exists(cur, "comments", "edit_token"):
            cur.execute("ALTER TABLE comments ADD COLUMN edit_token TEXT")
        if not _column_exists(cur, "comments", "edited_at"):
            cur.execute("ALTER TABLE comments ADD COLUMN edited_at TEXT")
        if not _column_exists(cur, "comments", "image_url"):
            cur.execute("ALTER TABLE comments ADD COLUMN image_url TEXT")
        if not _column_exists(cur, "comments", "media_type"):
            cur.execute("ALTER TABLE comments ADD COLUMN media_type TEXT")
        
        # Table des utilisateurs (pseudo + mot de passe)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                pseudo TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Table des réactions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES comments(id),
                emoji TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(comment_id, emoji)
            )
        """)
        
        # Import des versets si la table est vide
        cur.execute("SELECT COUNT(*) FROM verses")
        already_seeded = cur.fetchone()[0]
        if already_seeded == 0:
            cur.executemany(
                "INSERT INTO verses (reference, text) VALUES (%s, %s)",
                [(v["reference"], v["text"]) for v in VERSES],
            )
        
        conn.commit()
    finally:
        conn.close()


def get_daily_verse(db_path: str = DB_FILE) -> dict[str, str]:
    """Renvoie le même verset toute la journée, calculé de façon déterministe."""
    today = datetime.now().date()
    index = today.toordinal() % len(VERSES)
    verse = VERSES[index]
    return {"reference": verse["reference"], "text": verse["text"]}


def save_subscription(subscription: dict, db_path: str = DB_FILE) -> None:
    """Enregistre (ou met à jour) un abonnement aux notifications navigateur."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO subscriptions (endpoint, subscription_json, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (endpoint) DO UPDATE SET subscription_json = EXCLUDED.subscription_json
        """, (subscription["endpoint"], json.dumps(subscription), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    finally:
        conn.close()


def list_subscriptions(db_path: str = DB_FILE) -> list[dict]:
    """Renvoie tous les abonnements aux notifications."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT subscription_json FROM subscriptions")
        rows = cur.fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


def remove_subscriptions(endpoints: list[str], db_path: str = DB_FILE) -> None:
    """Supprime les abonnements aux notifications pour les endpoints donnés."""
    if not endpoints:
        return
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM subscriptions WHERE endpoint = %s", [(e,) for e in endpoints])
        conn.commit()
    finally:
        conn.close()


# Constantes pour les commentaires
ALLOWED_REACTIONS = ["❤️", "🙏", "", "🙌"]
MAX_PSEUDO_LENGTH = 30
MAX_COMMENT_LENGTH = 500
EDIT_WINDOW_SECONDS = 5 * 60


def add_comment(
    pseudo: str,
    text: str,
    parent_id: int | None = None,
    image_url: str | None = None,
    media_type: str | None = None,
    db_path: str = DB_FILE,
) -> dict:
    """Ajoute un commentaire (ou une réponse si parent_id est fourni)."""
    pseudo = pseudo.strip()
    text = text.strip()
    
    if not pseudo:
        raise ValueError("Le pseudo est requis.")
    if not text:
        raise ValueError("Le commentaire ne peut pas être vide.")
    if len(pseudo) > MAX_PSEUDO_LENGTH:
        raise ValueError(f"Le pseudo est limité à {MAX_PSEUDO_LENGTH} caractères.")
    if len(text) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Le commentaire est limité à {MAX_COMMENT_LENGTH} caractères.")
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        # Vérifie que le commentaire parent existe si c'est une réponse
        if parent_id is not None:
            cur.execute("SELECT id FROM comments WHERE id = %s", (parent_id,))
            if cur.fetchone() is None:
                raise ValueError("Le commentaire auquel tu réponds n'existe plus.")
        
        created_at = datetime.now().isoformat(timespec="seconds")
        edit_token = secrets.token_hex(16)
        
        cur.execute("""
            INSERT INTO comments
            (pseudo, text, parent_id, created_at, edit_token, image_url, media_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (pseudo, text, parent_id, created_at, edit_token, image_url, media_type))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        
        return {
            "id": new_id,
            "pseudo": pseudo,
            "text": text,
            "parent_id": parent_id,
            "created_at": created_at,
            "edited_at": None,
            "edit_token": edit_token,
            "image_url": image_url,
            "media_type": media_type,
            "reactions": {},
            "replies": [],
        }
    finally:
        conn.close()


def edit_comment(comment_id: int, edit_token: str, text: str, db_path: str = DB_FILE) -> dict:
    """Modifie le texte d'un commentaire si le edit_token correspond."""
    text = text.strip()
    
    if not text:
        raise ValueError("Le commentaire ne peut pas être vide.")
    if len(text) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Le commentaire est limité à {MAX_COMMENT_LENGTH} caractères.")
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT edit_token, created_at FROM comments WHERE id = %s", (comment_id,))
        row = cur.fetchone()
        
        if row is None:
            raise ValueError("Ce commentaire n'existe plus.")
        
        stored_token, created_at = row
        
        if not stored_token or not edit_token or stored_token != edit_token:
            raise ValueError("Tu ne peux modifier que tes propres commentaires.")
        
        elapsed = (datetime.now() - datetime.fromisoformat(created_at)).total_seconds()
        if elapsed > EDIT_WINDOW_SECONDS:
            raise ValueError("Le délai de modification (5 minutes) est dépassé.")
        
        edited_at = datetime.now().isoformat(timespec="seconds")
        cur.execute("UPDATE comments SET text = %s, edited_at = %s WHERE id = %s", (text, edited_at, comment_id))
        conn.commit()
        
        return {"id": comment_id, "text": text, "edited_at": edited_at}
    finally:
        conn.close()


def add_reaction(comment_id: int, emoji: str, db_path: str = DB_FILE) -> dict[str, int]:
    """Incrémente le compteur d'une réaction (emoji) sur un commentaire."""
    if emoji not in ALLOWED_REACTIONS:
        raise ValueError("Cette réaction n'est pas autorisée.")
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM comments WHERE id = %s", (comment_id,))
        if cur.fetchone() is None:
            raise ValueError("Ce commentaire n'existe plus.")
        
        cur.execute("""
            INSERT INTO reactions (comment_id, emoji, count) VALUES (%s, %s, 1)
            ON CONFLICT (comment_id, emoji) DO UPDATE SET count = reactions.count + 1
        """, (comment_id, emoji))
        
        conn.commit()
        
        cur.execute("SELECT emoji, count FROM reactions WHERE comment_id = %s", (comment_id,))
        rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


def remove_reaction(comment_id: int, emoji: str, db_path: str = DB_FILE) -> dict[str, int]:
    """Décrémente le compteur d'une réaction (emoji) sur un commentaire."""
    if emoji not in ALLOWED_REACTIONS:
        raise ValueError("Cette réaction n'est pas autorisée.")
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM comments WHERE id = %s", (comment_id,))
        if cur.fetchone() is None:
            raise ValueError("Ce commentaire n'existe plus.")
        
        cur.execute("UPDATE reactions SET count = GREATEST(count - 1, 0) WHERE comment_id = %s AND emoji = %s", (comment_id, emoji))
        cur.execute("DELETE FROM reactions WHERE comment_id = %s AND emoji = %s AND count <= 0", (comment_id, emoji))
        
        conn.commit()
        
        cur.execute("SELECT emoji, count FROM reactions WHERE comment_id = %s", (comment_id,))
        rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        conn.close()


def delete_comment(comment_id: int, edit_token: str, db_path: str = DB_FILE) -> bool:
    """Supprime un commentaire et ses réactions/réponses.
    - Si le commentaire a un edit_token : vérification stricte (sécurité)
    - Si le commentaire n'a PAS d'edit_token (ancien) : on accepte la suppression
    car il n'y a pas de moyen de vérifier l'auteur (compatibilité)"""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT edit_token FROM comments WHERE id = %s", (comment_id,))
        row = cur.fetchone()
        
        if row is None:
            return False  # Commentaire introuvable
        
        stored_token = row[0]
        
        # Si le commentaire a un token, on vérifie qu'il correspond
        if stored_token is not None and stored_token != edit_token:
            return False  # Token invalide
        
        # Suppression en cascade
        cur.execute("DELETE FROM reactions WHERE comment_id = %s", (comment_id,))
        cur.execute("DELETE FROM comments WHERE parent_id = %s", (comment_id,))
        cur.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
        
        conn.commit()
        return True
    finally:
        conn.close()


def list_comments(db_path: str = DB_FILE) -> list[dict]:
    """Renvoie tous les commentaires principaux avec leurs réactions et réponses."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        # Récupère tous les commentaires
        cur.execute("SELECT id, pseudo, text, parent_id, created_at, edited_at, image_url, media_type FROM comments")
        comment_rows = cur.fetchall()
        
        # Récupère toutes les réactions
        cur.execute("SELECT comment_id, emoji, count FROM reactions")
        reaction_rows = cur.fetchall()
        
        # Organise les réactions par commentaire
        reactions_by_comment: dict[int, dict[str, int]] = {}
        for comment_id, emoji, count in reaction_rows:
            reactions_by_comment.setdefault(comment_id, {})[emoji] = count
        
        # Construit le dictionnaire des commentaires
        by_id: dict[int, dict] = {}
        for comment_id, pseudo, text, parent_id, created_at, edited_at, image_url, media_type in comment_rows:
            by_id[comment_id] = {
                "id": comment_id,
                "pseudo": pseudo,
                "text": text,
                "parent_id": parent_id,
                "created_at": created_at,
                "edited_at": edited_at,
                "image_url": image_url,
                "media_type": media_type,
                "reactions": reactions_by_comment.get(comment_id, {}),
                "replies": [],
            }
        
        # Sépare les commentaires principaux des réponses
        top_level: list[dict] = []
        for comment in by_id.values():
            if comment["parent_id"] is not None and comment["parent_id"] in by_id:
                by_id[comment["parent_id"]]["replies"].append(comment)
            else:
                top_level.append(comment)
        
        # Trie les commentaires principaux par date (plus récents en premier)
        top_level.sort(key=lambda c: c["created_at"], reverse=True)
        
        # Trie les réponses par date (plus anciennes en premier)
        for comment in by_id.values():
            comment["replies"].sort(key=lambda c: c["created_at"])
        
        return top_level
    finally:
        conn.close()


# Constantes pour les comptes utilisateurs
MIN_PSEUDO_LENGTH = 3
MAX_USER_PSEUDO_LENGTH = 30
MIN_PASSWORD_LENGTH = 6


def create_user(pseudo: str, password: str, db_path: str = DB_FILE) -> dict:
    """Crée un nouveau compte utilisateur (pseudo unique + mot de passe
    hashé avec bcrypt). Lève ValueError si le pseudo est déjà pris ou si
    les champs ne respectent pas les contraintes de base."""
    pseudo = pseudo.strip()
    
    if len(pseudo) < MIN_PSEUDO_LENGTH or len(pseudo) > MAX_USER_PSEUDO_LENGTH:
        raise ValueError(f"Le pseudo doit contenir entre {MIN_PSEUDO_LENGTH} et {MAX_USER_PSEUDO_LENGTH} caractères.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    created_at = datetime.now().isoformat(timespec="seconds")
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM users WHERE LOWER(pseudo) = LOWER(%s)", (pseudo,))
        if cur.fetchone() is not None:
            raise ValueError("Ce pseudo est déjà utilisé.")
        
        cur.execute(
            "INSERT INTO users (pseudo, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id",
            (pseudo, password_hash, created_at),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        
        return {"id": user_id, "pseudo": pseudo}
    finally:
        conn.close()


def authenticate_user(pseudo: str, password: str, db_path: str = DB_FILE) -> dict:
    """Vérifie le pseudo/mot de passe. Lève ValueError si l'identifiant
    n'existe pas ou si le mot de passe est incorrect."""
    pseudo = pseudo.strip()
    
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, pseudo, password_hash FROM users WHERE LOWER(pseudo) = LOWER(%s)", (pseudo,))
        row = cur.fetchone()
        
        if row is None:
            raise ValueError("Pseudo ou mot de passe incorrect.")
        
        user_id, real_pseudo, password_hash = row
        
        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            raise ValueError("Pseudo ou mot de passe incorrect.")
        
        return {"id": user_id, "pseudo": real_pseudo}
    finally:
        conn.close()