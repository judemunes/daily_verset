import argparse
import asyncio
import json
import os
import random
import sqlite3
import shutil
import textwrap
import time
from datetime import datetime, timedelta

from colorama import Fore, Style, init

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Voix française naturelle par défaut pour le moteur edge-tts.
# Autres bonnes options : "fr-FR-DeniseNeural", "fr-CA-JeanNeural", "fr-CA-SylvieNeural"
DEFAULT_EDGE_VOICE = "fr-FR-HenriNeural"

# Base SQLite utilisée pour les versets, l'anti-répétition et le journal.
DB_FILE = "verset_du_jour.db"


VERSES = [
    {
        "reference": "Jean 3:16",
        "text": (
            "Car Dieu a tant aimé le monde qu'il a donné son Fils unique, "
            "afin que quiconque croit en lui ne périsse point, mais qu'il "
            "ait la vie éternelle."
        ),
    },
    {
        "reference": "Philippiens 4:13",
        "text": "Je puis tout par celui qui me fortifie.",
    },
    {
        "reference": "Psaume 23:1",
        "text": "L'Éternel est mon berger : je ne manquerai de rien.",
    },
    {
        "reference": "Proverbes 3:5-6",
        "text": (
            "Confie-toi en l'Éternel de tout ton cœur, et ne t'appuie pas "
            "sur ta sagesse ; reconnais-le dans toutes tes voies, et il "
            "aplanira tes sentiers."
        ),
    },
    {
        "reference": "Jérémie 29:11",
        "text": (
            "Car je connais les projets que j'ai formés sur vous, dit "
            "l'Éternel, projets de paix et non de malheur, afin de vous "
            "donner un avenir et de l'espérance."
        ),
    },
    {
        "reference": "Romains 8:28",
        "text": (
            "Nous savons, du reste, que toutes choses concourent au bien "
            "de ceux qui aiment Dieu, de ceux qui sont appelés selon son "
            "dessein."
        ),
    },
    {
        "reference": "Psaume 46:11",
        "text": (
            "Arrêtez, et sachez que je suis Dieu : je domine sur les "
            "nations, je domine sur la terre."
        ),
    },
    {
        "reference": "Ésaïe 40:31",
        "text": (
            "Mais ceux qui se confient en l'Éternel renouvellent leur "
            "force. Ils prennent le vol comme les aigles ; ils courent, et "
            "ne se lassent point, ils marchent, et ne se fatiguent point."
        ),
    },
    {
        "reference": "Matthieu 11:28",
        "text": (
            "Venez à moi, vous tous qui êtes fatigués et chargés, et je "
            "vous donnerai du repos."
        ),
    },
    {
        "reference": "Josué 1:9",
        "text": (
            "Ne t'ai-je pas donné cet ordre : Fortifie-toi et prends "
            "courage ? Ne t'effraie point et ne t'épouvante point, car "
            "l'Éternel, ton Dieu, est avec toi dans tout ce que tu "
            "entreprendras."
        ),
    },
    {
        "reference": "Psaume 119:105",
        "text": "Ta parole est une lampe à mes pieds, et une lumière sur mon sentier.",
    },
    {
        "reference": "1 Corinthiens 13:13",
        "text": (
            "Maintenant donc ces trois choses demeurent : la foi, "
            "l'espérance, la charité ; mais la plus grande de ces choses, "
            "c'est la charité."
        ),
    },
    {
        "reference": "Romains 12:12",
        "text": "Réjouissez-vous en espérance. Soyez patients dans l'affliction. Persévérez dans la prière.",
    },
    {
        "reference": "Psaume 34:9",
        "text": (
            "Sentez et voyez combien l'Éternel est bon ! Heureux l'homme "
            "qui cherche en lui son refuge !"
        ),
    },
    {
        "reference": "Galates 5:22-23",
        "text": (
            "Mais le fruit de l'Esprit, c'est l'amour, la joie, la paix, "
            "la patience, la bonté, la bénignité, la fidélité, la douceur, "
            "la tempérance ; la loi n'est pas contre ces choses."
        ),
    },
    {
        "reference": "Matthieu 5:16",
        "text": (
            "Que votre lumière luise ainsi devant les hommes, afin qu'ils "
            "voient vos bonnes œuvres, et qu'ils glorifient votre Père qui "
            "est dans les cieux."
        ),
    },
    {
        "reference": "Hébreux 11:1",
        "text": (
            "Or la foi est une ferme assurance des choses qu'on espère, "
            "une démonstration de celles qu'on ne voit pas."
        ),
    },
    {
        "reference": "Psaume 37:4",
        "text": "Fais de l'Éternel tes délices, et il te donnera ce que ton cœur désire.",
    },
    {
        "reference": "Colossiens 3:23",
        "text": (
            "Tout ce que vous faites, faites-le de bon cœur, comme pour le "
            "Seigneur et non pour des hommes."
        ),
    },
    {
        "reference": "Nombres 6:24-26",
        "text": (
            "Que l'Éternel te bénisse, et qu'il te garde ! Que l'Éternel "
            "fasse luire sa face sur toi, et qu'il t'accorde sa grâce ! "
            "Que l'Éternel tourne sa face vers toi, et qu'il te donne la "
            "paix !"
        ),
    },
    {
        "reference": "1 Corinthiens 13:13",
        "text": (
        "Maintenant, trois choses sont toujours là : la foi, l'espérance et l'amour. Mais la plus grande des trois, c'est l'amour."
        ),
    },
    {
        "reference": "Romains 12:9 ",
        "text": (
            "Que votre amour soit vrai. Détestez le mal, attachez-vous au bien."
        ),
    },
    {
        "reference": "Éphésiens 4:2",
        "text": (
            "Soyez simples, doux et patients, supportez-vous les uns les autres avec amour."
        ),
    },
    {
        "reference":"Éphésiens 4:31",
        "text": (
            "Ne gardez pas dans votre cœur le mal qu'on vous a fait. Ne vous énervez pas, ne vous mettez pas en colère, faites disparaître de chez vous les cris, les insultes, le mal sous toutes ses formes."
        ),

    },
    {
        "reference": "Proverbes 22:24 ",
        "text":(
            "Ne deviens pas l'ami d'un homme coléreux. Ne va pas avec quelqu'un qui se met en colère facilement."
        )
    }
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
    print(
        border_color
        + "║  "
        + reference_color
        + reference.rjust(inside_width)
        + border_color
        + "  ║"
    )
    print("╚" + "═" * (card_width - 2) + "╝" + Style.RESET_ALL)
    print()


def get_connection(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def init_db(db_path: str) -> None:
    """Crée les tables si besoin et importe VERSES dans la table 'verses'
    au tout premier lancement (elle ne sera plus jamais réécrite après)."""

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                shown_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verse_id INTEGER NOT NULL REFERENCES verses(id),
                logged_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL UNIQUE,
                subscription_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        already_seeded = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        if already_seeded == 0:
            conn.executemany(
                "INSERT INTO verses (reference, text) VALUES (?, ?)",
                [(v["reference"], v["text"]) for v in VERSES],
            )
        conn.commit()
    finally:
        conn.close()


def choose_verse(db_path: str = DB_FILE) -> dict[str, str]:
    """Tire un verset au hasard depuis la base en évitant de répéter les
    derniers déjà vus (table 'history'). Dès que tous les versets sont
    passés, le cycle recommence automatiquement.

    Utilisé uniquement par le CLI local (run_once/run_daemon) : la version
    web utilise get_daily_verse(), qui est déterministe et ne dépend pas de
    la persistance du fichier SQLite (voir plus bas)."""

    conn = get_connection(db_path)
    try:
        all_verses = conn.execute("SELECT id, reference, text FROM verses").fetchall()
        if not all_verses:
            raise RuntimeError("La table 'verses' est vide.")

        max_history = max(len(all_verses) - 1, 1)
        recent_ids = {
            row[0]
            for row in conn.execute(
                "SELECT verse_id FROM history ORDER BY id DESC LIMIT ?",
                (max_history,),
            ).fetchall()
        }

        remaining = [v for v in all_verses if v[0] not in recent_ids] or all_verses
        verse_id, reference, text = random.choice(remaining)

        conn.execute(
            "INSERT INTO history (verse_id, shown_at) VALUES (?, ?)",
            (verse_id, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return {"reference": reference, "text": text}
    finally:
        conn.close()


def get_daily_verse(db_path: str = DB_FILE) -> dict[str, str]:
    """Renvoie le même verset jusqu'à la prochaine bascule, calculée de
    façon déterministe (aucune base de données requise).

    Comme le plan gratuit de Render a un système de fichiers éphémère (le
    fichier SQLite est réinitialisé à chaque redémarrage/mise en veille du
    service), on ne peut pas se fier à un historique persistant pour savoir
    quel verset a déjà été montré. À la place, on calcule un index à partir
    d'un "jour effectif" qui ne bascule qu'à l'heure définie par la variable
    d'environnement PUSH_TIME (8h par défaut, la même heure que la
    notification quotidienne) plutôt qu'à minuit :
    - avant 8h, on affiche encore le verset d'hier
    - à partir de 8h (inclus), on affiche le verset du jour

    Ce calcul est identique pour tous les visiteurs et ne change qu'une
    fois par jour, peu importe combien de fois le serveur redémarre
    entre-temps.

    Le paramètre db_path est conservé pour compatibilité avec les appelants
    existants (server.py), mais n'est plus utilisé ici.
    """

    push_hour, push_minute = (
        int(part) for part in os.environ.get("PUSH_TIME", "08:00").split(":")
    )

    now = datetime.now()
    threshold_today = now.replace(hour=push_hour, minute=push_minute, second=0, microsecond=0)

    effective_date = now.date() if now >= threshold_today else (now - timedelta(days=1)).date()

    index = effective_date.toordinal() % len(VERSES)
    verse = VERSES[index]
    return {"reference": verse["reference"], "text": verse["text"]}


def save_subscription(subscription: dict, db_path: str = DB_FILE) -> None:
    """Enregistre (ou met à jour) un abonnement aux notifications navigateur."""

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO subscriptions (endpoint, subscription_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET subscription_json = excluded.subscription_json
            """,
            (subscription["endpoint"], json.dumps(subscription), datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def list_subscriptions(db_path: str = DB_FILE) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT subscription_json FROM subscriptions").fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


def remove_subscriptions(endpoints: list[str], db_path: str = DB_FILE) -> None:
    if not endpoints:
        return
    conn = get_connection(db_path)
    try:
        conn.executemany("DELETE FROM subscriptions WHERE endpoint = ?", [(e,) for e in endpoints])
        conn.commit()
    finally:
        conn.close()


def export_verse_journal(verse: dict[str, str], db_path: str = DB_FILE) -> None:
    """Ajoute le verset du jour à la table 'journal' de la base SQLite."""

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM verses WHERE reference = ? AND text = ?",
            (verse["reference"], verse["text"]),
        ).fetchone()
        if row is None:
            print(
                Fore.YELLOW
                + "Verset introuvable en base, journal non mis à jour."
                + Style.RESET_ALL
            )
            return

        conn.execute(
            "INSERT INTO journal (verse_id, logged_at) VALUES (?, ?)",
            (row[0], datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        print(Fore.GREEN + f"Verset ajouté au journal (base : {db_path})" + Style.RESET_ALL)
    except sqlite3.Error as exc:
        print(Fore.YELLOW + f"Impossible d'écrire dans le journal ({exc})." + Style.RESET_ALL)
    finally:
        conn.close()


def find_french_voice_id(engine) -> str | None:
    """Scan the system voices installed on this machine and return the id of
    the first one that speaks French, so verses aren't read with an English
    (or other) accent by mistake."""

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


def speak_verse_pyttsx3(verse: dict[str, str], rate: int, volume: float, voice_id: str | None) -> None:
    """Read the verse aloud using the offline TTS engine (pyttsx3 / SAPI5)."""

    if not TTS_AVAILABLE:
        print(
            Fore.RED
            + "pyttsx3 n'est pas installé. Installe-le avec : pip install pyttsx3"
            + Style.RESET_ALL
        )
        return

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)

    chosen_voice_id = voice_id or find_french_voice_id(engine)
    if chosen_voice_id:
        engine.setProperty("voice", chosen_voice_id)
    else:
        print(
            Fore.YELLOW
            + "Aucune voix française trouvée sur ce système : la voix par "
            + "défaut sera utilisée (accent possiblement non-francophone). "
            + "Utilise --list-voices pour voir les voix installées."
            + Style.RESET_ALL
        )

    speech_text = f"{verse['reference']}. {verse['text']}"
    engine.say(speech_text)
    engine.runAndWait()
    engine.stop()


async def _speak_verse_edge_async(speech_text: str, voice: str, rate: int) -> None:
    # edge-tts expects a signed rate string like "+10%" or "-15%".
    # We convert the pyttsx3-style words-per-minute value into a rough
    # percentage offset from a natural baseline (~175 wpm).
    percent_offset = round(((rate - 175) / 175) * 100)
    rate_str = f"{'+' if percent_offset >= 0 else ''}{percent_offset}%"

    communicator = edge_tts.Communicate(speech_text, voice=voice, rate=rate_str)
    output_path = "verse_audio.mp3"
    await communicator.save(output_path)
    return output_path


def speak_verse_edge(verse: dict[str, str], rate: int, edge_voice: str) -> None:
    """Read the verse aloud using edge-tts: free, online, near-human-quality
    neural voices from Microsoft (much more natural than offline SAPI voices)."""

    if not EDGE_TTS_AVAILABLE:
        print(
            Fore.RED
            + "edge-tts n'est pas installé. Installe-le avec : pip install edge-tts"
            + Style.RESET_ALL
        )
        return

    speech_text = f"{verse['reference']}. {verse['text']}"
    output_path = asyncio.run(_speak_verse_edge_async(speech_text, edge_voice, rate))

    # Play the generated mp3. playsound is lightweight and cross-platform.
    try:
        from playsound import playsound
        playsound(output_path)
    except ImportError:
        print(
            Fore.YELLOW
            + f"Audio généré dans {output_path}, mais 'playsound' n'est pas installé "
            + "pour le lire automatiquement. Installe-le avec : pip install playsound==1.2.2"
            + Style.RESET_ALL
        )


def speak_verse(
    verse: dict[str, str],
    rate: int = 165,
    volume: float = 1.0,
    voice_id: str | None = None,
    engine_name: str = "pyttsx3",
    edge_voice: str = DEFAULT_EDGE_VOICE,
) -> None:
    """Read the verse aloud using the chosen TTS engine."""

    if engine_name == "edge":
        speak_verse_edge(verse, rate=rate, edge_voice=edge_voice)
    else:
        speak_verse_pyttsx3(verse, rate=rate, volume=volume, voice_id=voice_id)


def list_voices() -> None:
    """Print the available system voices with their IDs, useful for --voice-id."""

    if not TTS_AVAILABLE:
        print(
            Fore.RED
            + "pyttsx3 n'est pas installé. Installe-le avec : pip install pyttsx3"
            + Style.RESET_ALL
        )
        return

    engine = pyttsx3.init()
    for voice in engine.getProperty("voices"):
        print(f"{voice.id}  —  {voice.name}")
    engine.stop()


def run_once(args: argparse.Namespace) -> None:
    init(autoreset=True)
    init_db(args.db_path)
    verse = choose_verse(args.db_path)
    display_verse(verse)
    if not args.no_voice:
        speak_verse(
            verse,
            rate=args.rate,
            volume=args.volume,
            voice_id=args.voice_id,
            engine_name=args.engine,
            edge_voice=args.edge_voice,
        )
    if args.export_json:
        export_verse_journal(verse, args.db_path)


def run_daemon(args: argparse.Namespace) -> None:
    """Stay running and speak/display a verse once per day at HH:MM (local time)."""

    target_hour, target_minute = (int(part) for part in args.at.split(":"))
    print(
        Fore.GREEN
        + f"Mode planification actif : un verset sera lu chaque jour à {args.at}."
        + " (laisse ce programme tourner en arrière-plan)"
        + Style.RESET_ALL
    )
    last_run_date = None
    while True:
        now = datetime.now()
        if (
            now.hour == target_hour
            and now.minute == target_minute
            and last_run_date != now.date()
        ):
            run_once(args)
            last_run_date = now.date()
        time.sleep(20)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Affiche et lit un verset biblique du jour.")
    parser.add_argument("--no-voice", action="store_true", help="Désactive la lecture vocale.")
    parser.add_argument("--rate", type=int, default=165, help="Vitesse de la voix (mots/minute).")
    parser.add_argument("--volume", type=float, default=1.0, help="Volume de la voix (0.0 à 1.0).")
    parser.add_argument("--voice-id", type=str, default=None, help="ID de la voix système à utiliser (pyttsx3).")
    parser.add_argument("--list-voices", action="store_true", help="Liste les voix disponibles (pyttsx3) et quitte.")
    parser.add_argument(
        "--engine",
        choices=["pyttsx3", "edge"],
        default="pyttsx3",
        help=(
            "Moteur de synthèse vocale. 'pyttsx3' = voix système hors-ligne (rapide, "
            "qualité robotique). 'edge' = voix neuronale Microsoft, gratuite, en ligne, "
            "beaucoup plus naturelle. Défaut : pyttsx3."
        ),
    )
    parser.add_argument(
        "--edge-voice",
        type=str,
        default=DEFAULT_EDGE_VOICE,
        help=f"Voix edge-tts à utiliser. Défaut : {DEFAULT_EDGE_VOICE}.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Reste en cours d'exécution et lit un verset chaque jour à l'heure donnée par --at.",
    )
    parser.add_argument(
        "--at",
        type=str,
        default="08:00",
        help="Heure quotidienne (HH:MM, 24h) utilisée avec --daemon. Défaut : 08:00.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DB_FILE,
        help=f"Fichier de base de données SQLite (versets, historique, journal). Défaut : {DB_FILE}.",
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Ajoute le verset du jour à la table 'journal' de la base SQLite.",
    )
    return parser


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