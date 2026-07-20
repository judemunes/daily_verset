import base64
import os
import re
import uuid

from apscheduler.schedulers.background import BackgroundScheduler#explication: ce fichier est le fichier qui permet de planifier des tâches
from fastapi import FastAPI, Request#explication: ce fichier est le fichier qui permet de créer une API
from fastapi.responses import FileResponse, JSONResponse#explication: ce fichier est le fichier qui permet de renvoyer des réponses HTTP
from fastapi.staticfiles import StaticFiles#explication: ce fichier est le fichier qui permet de servir des fichiers statiques

#explication: ce fichier est le fichier qui permet d'envoyer les notifications push
import push
from verset_du_jour import (
    DB_FILE,
    add_comment,
    add_reaction,
    edit_comment,
    get_daily_verse,
    init_db,
    list_comments,
    list_subscriptions,
    remove_reaction,
    remove_subscriptions,
    save_subscription,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 Mo
MAX_VIDEO_BYTES = 30 * 1024 * 1024  # 30 Mo
ALLOWED_IMAGE_TYPES = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}
ALLOWED_VIDEO_TYPES = {"mp4": "mp4", "webm": "webm", "ogg": "ogv", "quicktime": "mov"}

# Heure quotidienne d'envoi de la notification (24h, heure du serveur).
# Modifiable via la variable d'environnement PUSH_TIME, ex: "07:30".
PUSH_HOUR, PUSH_MINUTE = (int(p) for p in os.environ.get("PUSH_TIME", "08:00").split(":"))
#explication: ce fichier est le fichier qui permet de créer une API
app = FastAPI(title="Verset du jour")
#explication: ce fichier est le fichier qui permet de planifier des tâches
scheduler = BackgroundScheduler()

#explication: ce fichier est le fichier qui permet d'envoyer la notification quotidienne
def send_daily_notification() -> None:
    verse = get_daily_verse(DB_FILE)
    subscriptions = list_subscriptions(DB_FILE)
    if not subscriptions:
        return
    dead_endpoints = push.send_push_to_all(
        subscriptions,
        payload={
            "title": "Verset du jour",
            "body": f"{verse['text']}  — {verse['reference']}",
        },
    )
    remove_subscriptions(dead_endpoints, DB_FILE)


@app.on_event("startup")#explication: ce fichier est le fichier qui permet de démarrer le serveur
def on_startup() -> None:
    init_db(DB_FILE)
    scheduler.add_job(
        send_daily_notification,
        trigger="cron",
        hour=PUSH_HOUR,
        minute=PUSH_MINUTE,
        id="daily_push",
        replace_existing=True,
    )
    scheduler.start()


@app.on_event("shutdown")#explication: ce fichier est le fichier qui permet d'arrêter le serveur
def on_shutdown() -> None:
    scheduler.shutdown(wait=False)


@app.get("/api/verset")#explication: ce fichier est le fichier qui permet de récupérer le verset du jour
def api_verset() -> dict[str, str]:
    return get_daily_verse(DB_FILE)
def api_verset() -> dict[str, str]:
    return get_daily_verse(DB_FILE)


@app.get("/api/vapid-public-key")#explication: ce fichier est le fichier qui permet de récupérer la clé publique VAPID
def api_vapid_public_key() -> dict[str, str]:
    return {"publicKey": push.get_vapid_public_key()}


#explication: ce fichier est le fichier qui permet d'abonner un utilisateur
@app.post("/api/subscribe")#explication: ce fichier est le fichier qui permet d'abonner un utilisateur
async def api_subscribe(request: Request) -> JSONResponse:
    subscription = await request.json()
    save_subscription(subscription, DB_FILE)
    return JSONResponse({"status": "ok"})

#explication: ce fichier est le fichier qui permet de désabonner un utilisateur
@app.post("/api/unsubscribe")#explication: ce fichier est le fichier qui permet de désabonner un utilisateur
async def api_unsubscribe(request: Request) -> JSONResponse:
    body = await request.json()
    endpoint = body.get("endpoint")
    if endpoint:
        remove_subscriptions([endpoint], DB_FILE)
    return JSONResponse({"status": "ok"})

#explication: onglet Communauté : récupérer tous les commentaires (avec réponses et réactions)
@app.get("/api/comments")
def api_list_comments() -> list[dict]:
    return list_comments(DB_FILE)


#explication: décode un média (image ou vidéo) envoyé en base64 (data URL)
#depuis le navigateur et l'enregistre dans static/uploads, puis renvoie
#son URL publique et son type ("image" ou "video") (ou (None, None) si
#aucun média n'est fourni).
def save_comment_media(data_url: str | None) -> tuple[str | None, str | None]:
    if not data_url:
        return None, None

    match = re.match(r"^data:(image|video)/([\w.+-]+);base64,(.+)$", data_url)
    if not match:
        raise ValueError("Format de média non pris en charge.")

    kind, subtype, encoded = match.group(1), match.group(2).lower(), match.group(3)
    allowed = ALLOWED_IMAGE_TYPES if kind == "image" else ALLOWED_VIDEO_TYPES
    extension = allowed.get(subtype)
    if not extension:
        raise ValueError(
            "Type d'image non autorisé (jpg, png, gif, webp uniquement)."
            if kind == "image"
            else "Type de vidéo non autorisé (mp4, webm, ogg, mov uniquement)."
        )

    try:
        raw = base64.b64decode(encoded)
    except Exception as exc:
        raise ValueError("Média invalide.") from exc

    max_bytes = MAX_IMAGE_BYTES if kind == "image" else MAX_VIDEO_BYTES
    if len(raw) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValueError(f"Le fichier dépasse la taille maximale autorisée ({limit_mb} Mo).")

    filename = f"{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(UPLOADS_DIR, filename), "wb") as f:
        f.write(raw)

    return f"/static/uploads/{filename}", kind


#explication: onglet Communauté : poster un commentaire, ou une réponse si parent_id est fourni
@app.post("/api/comments")
async def api_add_comment(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        image_url, media_type = save_comment_media(body.get("image"))
        comment = add_comment(
            pseudo=body.get("pseudo", ""),
            text=body.get("text", ""),
            parent_id=body.get("parent_id"),
            image_url=image_url,
            media_type=media_type,
            db_path=DB_FILE,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse(comment)


#explication: onglet Communauté : modifier son propre commentaire (dans les 5 minutes suivant l'envoi)
@app.put("/api/comments/{comment_id}")
async def api_edit_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    try:
        result = edit_comment(
            comment_id,
            edit_token=body.get("edit_token", ""),
            text=body.get("text", ""),
            db_path=DB_FILE,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse(result)


#explication: onglet Communauté : ajouter une réaction (emoji) sur un commentaire
@app.post("/api/comments/{comment_id}/react")
async def api_react_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    try:
        reactions = add_reaction(comment_id, body.get("emoji", ""), db_path=DB_FILE)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"reactions": reactions})


#explication: onglet Communauté : retirer sa réaction (emoji) sur un commentaire
@app.post("/api/comments/{comment_id}/unreact")
async def api_unreact_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    try:
        reactions = remove_reaction(comment_id, body.get("emoji", ""), db_path=DB_FILE)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"reactions": reactions})


#explication: ce fichier est le fichier qui permet de servir la page d'accueil
@app.get("/")#explication: ce fichier est le fichier qui permet de servir la page d'accueil
def index() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))#explication: ce fichier est le fichier qui permet de servir la page d'accueil


app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")#explication: ce fichier est le fichier qui permet de servir les fichiers statiques
