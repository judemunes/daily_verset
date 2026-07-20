import argparse
import asyncio
import json
import os
import random
import secrets
import shutil
import textwrap
import time
from datetime import datetime

import psycopg2
import psycopg2.errors
from colorama import Fore, Style, init

try:
    import pyttsx3  # type: ignore
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import edge_tts  # type: ignore
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

DEFAULT_EDGE_VOICE = "fr-FR-HenriNeural"

DB_FILE = os.environ.get(
    "DATABASE_URL",
    os.environ.get("DB_FILE", "postgresql://postgres:postgres@localhost:5432/verset_du_jour"),
)

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

def display_verse(verse: dict[str, str]) -> None:
    card_width = min(max(shutil.get_terminal_size().columns - 4, 40), 76)
    inside_width = card_width - 4
    wrapped_lines = textwrap.wrap(f'«\u00a0{verse["text"]}\u00a0»', width=inside_width)
    border_color = Fore.CYAN
    text_color = Fore.WHITE
    reference_color = Fore.YELLOW + Style.BRIGHT
    print()
    print(border_color + "╔" + "═" * (card_width - 2) + "╗")
    print("║" + Style.BRIGHT + " VERSET DU JOUR ".center(card_width - 2) + Style.NORMAL + "║")
    timestamp = datetime.now().strftime("%d/%m/%Y — %H:%M:%S")
    print("║" + Fore.LIGHTBLACK_EX + timestamp.center(card_width - 2) + border_color + "║")
    print("╠" + "═" * (card_width - 2) + "╣")
    for line in wrapped_lines:
        print(border_color + "║  " + text_color + line.ljust(inside_width) + border_color + "  ║")
    print("║" + " " * (card_width - 2) + "║")
    reference = f"— {verse['reference']}"
    print(border_color + "║  " + reference_color + reference.rjust(inside_width) + border_color + "  ║")
    print("╚" + "═" * (card_width - 2) + "╝" + Style.RESET_ALL)
    print()

def get_connection(db_path: str) -> "psycopg2.extensions.connection":
    return psycopg2.connect(db_path)

def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None

def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verses (
                id SERIAL PRIMARY KEY,
                reference TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                shown_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id SERIAL PRIMARY KEY,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                logged_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                endpoint TEXT NOT NULL UNIQUE,
                subscription_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
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
        if not _column_exists(cur, "comments", "edit_token"):
            cur.execute("ALTER TABLE comments ADD COLUMN edit_token TEXT")
        if not _column_exists(cur, "comments", "edited_at"):
            cur.execute("ALTER TABLE comments ADD COLUMN edited_at TEXT")
        if not _column_exists(cur, "comments", "image_url"):
            cur.execute("ALTER TABLE comments ADD COLUMN image_url TEXT")
        if not _column_exists(cur, "comments", "media_type"):
            cur.execute("ALTER TABLE comments ADD COLUMN media_type TEXT")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES comments(id),
                emoji TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(comment_id, emoji)
            )
        """)
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

def choose_verse(db_path: str = DB_FILE) -> dict[str, str]:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, reference, text FROM verses")
        all_verses = cur.fetchall()
        if not all_verses:
            raise RuntimeError("La table 'verses' est vide.")
        max_history = max(len(all_verses) - 1, 1)
        cur.execute("SELECT verse_id FROM history ORDER BY id DESC LIMIT %s", (max_history,))
        recent_ids = {row[0] for row in cur.fetchall()}
        remaining = [v for v in all_verses if v[0] not in recent_ids] or all_verses
        verse_id, reference, text = random.choice(remaining)
        cur.execute("INSERT INTO history (verse_id, shown_at) VALUES (%s, %s)", (verse_id, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return {"reference": reference, "text": text}
    finally:
        conn.close()

def get_daily_verse(db_path: str = DB_FILE) -> dict[str, str]:
    today = datetime.now().date()
    index = today.toordinal() % len(VERSES)
    verse = VERSES[index]
    return {"reference": verse["reference"], "text": verse["text"]}

def save_subscription(subscription: dict, db_path: str = DB_FILE) -> None:
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
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT subscription_json FROM subscriptions")
        rows = cur.fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()

def remove_subscriptions(endpoints: list[str], db_path: str = DB_FILE) -> None:
    if not endpoints:
        return
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.executemany("DELETE FROM subscriptions WHERE endpoint = %s", [(e,) for e in endpoints])
        conn.commit()
    finally:
        conn.close()

ALLOWED_REACTIONS = ["❤️", "🙏", "👏", "🙌"]
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
#fonction pour supprimer un commentaire et ses reponses et ses reactions  
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
#fonction pour lister les commentaires avec leurs reponses et leurs reactions 
def list_comments(db_path: str = DB_FILE) -> list[dict]:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, pseudo, text, parent_id, created_at, edited_at, image_url, media_type FROM comments")
        comment_rows = cur.fetchall()
        cur.execute("SELECT comment_id, emoji, count FROM reactions")
        reaction_rows = cur.fetchall()
        reactions_by_comment: dict[int, dict[str, int]] = {}
        for comment_id, emoji, count in reaction_rows:
            reactions_by_comment.setdefault(comment_id, {})[emoji] = count
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
        top_level: list[dict] = []
        for comment in by_id.values():
            if comment["parent_id"] is not None and comment["parent_id"] in by_id:
                by_id[comment["parent_id"]]["replies"].append(comment)
            else:
                top_level.append(comment)
        top_level.sort(key=lambda c: c["created_at"], reverse=True)
        for comment in by_id.values():
            comment["replies"].sort(key=lambda c: c["created_at"])
        return top_level
    finally:
        conn.close()
#fonction pour exporter le verset en journal pour tous les utilisateurs
def export_verse_journal(verse: dict[str, str], db_path: str = DB_FILE) -> None:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM verses WHERE reference = %s AND text = %s", (verse["reference"], verse["text"]))
        row = cur.fetchone()
        if row is None:
            print(Fore.YELLOW + "Verset introuvable en base, journal non mis à jour." + Style.RESET_ALL)
            return
        cur.execute("INSERT INTO journal (verse_id, logged_at) VALUES (%s, %s)", (row[0], datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        print(Fore.GREEN + f"Verset ajouté au journal (base : {db_path})" + Style.RESET_ALL)
    except psycopg2.Error as exc:
        print(Fore.YELLOW + f"Impossible d'écrire dans le journal ({exc})." + Style.RESET_ALL)
    finally:
        conn.close()
#fonction pour trouver la voix française  tts
def find_french_voice_id(engine) -> str | None:
    for voice in engine.getProperty("voices"):
        languages = getattr(voice, "languages", None) or []
        decoded_languages = []
        for lang in languages:
            if isinstance(lang, bytes):
                decoded_languages.append(lang.decode(errors="ignore").lower())
            else:
                decoded_languages.append(str(lang).lower())
        haystack = " ".join([voice.id.lower(), voice.name.lower(), *decoded_languages])
        if "fr" in decoded_languages or "french" in haystack or "fr-fr" in haystack or "fr_fr" in haystack:
            return voice.id
    return None
#fonction pour parler le verset en pyttsx3
def speak_verse_pyttsx3(verse: dict[str, str], rate: int, volume: float, voice_id: str | None) -> None:
    if not TTS_AVAILABLE:
        print(Fore.RED + "pyttsx3 n'est pas installé. Installe-le avec : pip install pyttsx3" + Style.RESET_ALL)
        return
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)
    chosen_voice_id = voice_id or find_french_voice_id(engine)
    if chosen_voice_id:
        engine.setProperty("voice", chosen_voice_id)
    else:
        print(Fore.YELLOW + "Aucune voix française trouvée sur ce système : la voix par défaut sera utilisée." + Style.RESET_ALL)
    speech_text = f"{verse['reference']}. {verse['text']}"
    engine.say(speech_text)
    engine.runAndWait()
    engine.stop()
#fonction pour parler le verset en edge-tts
async def _speak_verse_edge_async(speech_text: str, voice: str, rate: int) -> None:
    percent_offset = round(((rate - 175) / 175) * 100)
    rate_str = f"{'+' if percent_offset >= 0 else ''}{percent_offset}%"
    communicator = edge_tts.Communicate(speech_text, voice=voice, rate=rate_str)
    output_path = "verse_audio.mp3"
    await communicator.save(output_path)
    return output_path
#fonction pour parler le verset en edge-tts  
def speak_verse_edge(verse: dict[str, str], rate: int, edge_voice: str) -> None:
    if not EDGE_TTS_AVAILABLE:
        print(Fore.RED + "edge-tts n'est pas installé. Installe-le avec : pip install edge-tts" + Style.RESET_ALL)
        return
    speech_text = f"{verse['reference']}. {verse['text']}"
    output_path = asyncio.run(_speak_verse_edge_async(speech_text, edge_voice, rate))
    try:
        from playsound import playsound  # type: ignore
        playsound(output_path)
    except ImportError:
        print(Fore.YELLOW + f"Audio généré dans {output_path}, mais 'playsound' n'est pas installé." + Style.RESET_ALL)
#fonction pour parler le verset en edge-tts ou pyttsx3  
def speak_verse(verse: dict[str, str], rate: int = 165, volume: float = 1.0, voice_id: str | None = None, engine_name: str = "pyttsx3", edge_voice: str = DEFAULT_EDGE_VOICE) -> None:
    if engine_name == "edge":
        speak_verse_edge(verse, rate=rate, edge_voice=edge_voice)
    else:
        speak_verse_pyttsx3(verse, rate=rate, volume=volume, voice_id=voice_id)
#fonction pour lister les voix disponibles
def list_voices() -> None:
    if not TTS_AVAILABLE:
        print(Fore.RED + "pyttsx3 n'est pas installé. Installe-le avec : pip install pyttsx3" + Style.RESET_ALL)
        return
    engine = pyttsx3.init()
    for voice in engine.getProperty("voices"):
        print(f"{voice.id}  —  {voice.name}")
    engine.stop()
#fonction pour exécuter le verset du jour en mode console 
def run_once(args: argparse.Namespace) -> None:
    init(autoreset=True)
    init_db(args.db_path)
    verse = choose_verse(args.db_path)
    display_verse(verse)
    if not args.no_voice:
        speak_verse(verse, rate=args.rate, volume=args.volume, voice_id=args.voice_id, engine_name=args.engine, edge_voice=args.edge_voice)
    if args.export_json:
        export_verse_journal(verse, args.db_path)
#fonction pour exécuter le verset du jour en mode planification
def run_daemon(args: argparse.Namespace) -> None:
    target_hour, target_minute = (int(part) for part in args.at.split(":"))
    print(Fore.GREEN + f"Mode planification actif : un verset sera lu chaque jour à {args.at}." + Style.RESET_ALL)
    last_run_date = None
    while True:
        now = datetime.now()
        if now.hour == target_hour and now.minute == target_minute and last_run_date != now.date():
            run_once(args)
            last_run_date = now.date()
        time.sleep(20)
#fonction pour construire le parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Affiche et lit un verset biblique du jour.")
    parser.add_argument("--no-voice", action="store_true", help="Désactive la lecture vocale.")
    parser.add_argument("--rate", type=int, default=165, help="Vitesse de la voix (mots/minute).")
    parser.add_argument("--volume", type=float, default=1.0, help="Volume de la voix (0.0 à 1.0).")
    parser.add_argument("--voice-id", type=str, default=None, help="ID de la voix système à utiliser (pyttsx3).")
    parser.add_argument("--list-voices", action="store_true", help="Liste les voix disponibles (pyttsx3) et quitte.")
    parser.add_argument("--engine", choices=["pyttsx3", "edge"], default="pyttsx3", help="Moteur de synthèse vocale.")
    parser.add_argument("--edge-voice", type=str, default=DEFAULT_EDGE_VOICE, help=f"Voix edge-tts à utiliser. Défaut : {DEFAULT_EDGE_VOICE}.")
    parser.add_argument("--daemon", action="store_true", help="Reste en cours d'exécution et lit un verset chaque jour à l'heure donnée par --at.")
    parser.add_argument("--at", type=str, default="08:00", help="Heure quotidienne (HH:MM, 24h) utilisée avec --daemon.")
    parser.add_argument("--db-path", type=str, default=DB_FILE, help=f"Chaîne de connexion PostgreSQL.")
    parser.add_argument("--export-json", action="store_true", help="Ajoute le verset du jour à la table 'journal'.")
    return parser
#fonction main   
def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.list_voices:
        list_voices()
        return
    if args.daemon:
        run_daemon(args)
    else:
        run_once(args)

if __name__ == "__main__":
    main()