import base64
import os
import re

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import push
from verset_du_jour import (
    DB_FILE,
    add_comment,
    add_reaction,
    delete_comment,
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

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 Mo
MAX_VIDEO_BYTES = 30 * 1024 * 1024  # 30 Mo
ALLOWED_IMAGE_TYPES = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}
ALLOWED_VIDEO_TYPES = {"mp4": "mp4", "webm": "webm", "ogg": "ogv", "quicktime": "mov"}

PUSH_HOUR, PUSH_MINUTE = (int(p) for p in os.environ.get("PUSH_TIME", "08:00").split(":"))

app = FastAPI(title="Verset du jour")
scheduler = BackgroundScheduler()

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

@app.on_event("startup")
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

@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler.shutdown(wait=False)

@app.get("/api/verset")
def api_verset() -> dict[str, str]:
    return get_daily_verse(DB_FILE)

@app.get("/api/vapid-public-key")
def api_vapid_public_key() -> dict[str, str]:
    return {"publicKey": push.get_vapid_public_key()}

@app.post("/api/subscribe")
async def api_subscribe(request: Request) -> JSONResponse:
    subscription = await request.json()
    save_subscription(subscription, DB_FILE)
    return JSONResponse({"status": "ok"})

@app.post("/api/unsubscribe")
async def api_unsubscribe(request: Request) -> JSONResponse:
    body = await request.json()
    endpoint = body.get("endpoint")
    if endpoint:
        remove_subscriptions([endpoint], DB_FILE)
    return JSONResponse({"status": "ok"})

@app.get("/api/comments")
def api_list_comments() -> list[dict]:
    return list_comments(DB_FILE)

def save_comment_media(data_url: str | None) -> tuple[str | None, str | None]:
    if not data_url:
        return None, None

    match = re.match(r"^data:(image|video)/([\w.+-]+);base64,(.+)$", data_url)
    if not match:
        raise ValueError("Format de média non pris en charge.")

    kind, subtype = match.group(1), match.group(2).lower()
    allowed = ALLOWED_IMAGE_TYPES if kind == "image" else ALLOWED_VIDEO_TYPES
    extension = allowed.get(subtype)
    if not extension:
        raise ValueError(
            "Type d'image non autorisé (jpg, png, gif, webp uniquement)."
            if kind == "image"
            else "Type de vidéo non autorisé (mp4, webm, ogg, mov uniquement)."
        )

    try:
        encoded = match.group(3)
        raw = base64.b64decode(encoded)
    except Exception as exc:
        raise ValueError("Média invalide.") from exc

    max_bytes = MAX_IMAGE_BYTES if kind == "image" else MAX_VIDEO_BYTES
    if len(raw) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValueError(f"Le fichier dépasse la taille maximale autorisée ({limit_mb} Mo).")

    return data_url, kind

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

# Après la route PUT (api_edit_comment), ajoute :
@app.delete("/api/comments/{comment_id}")
async def api_delete_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    edit_token = body.get("edit_token", "")
    
    success = delete_comment(comment_id, edit_token, db_path=DB_FILE)
    if not success:
        return JSONResponse({"error": "Tu ne peux supprimer que tes propres commentaires."}, status_code=403)
    
    return JSONResponse({"status": "ok"})

@app.post("/api/comments/{comment_id}/react")
async def api_react_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    try:
        reactions = add_reaction(comment_id, body.get("emoji", ""), db_path=DB_FILE)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"reactions": reactions})

@app.post("/api/comments/{comment_id}/unreact")
async def api_unreact_comment(comment_id: int, request: Request) -> JSONResponse:
    body = await request.json()
    try:
        reactions = remove_reaction(comment_id, body.get("emoji", ""), db_path=DB_FILE)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"reactions": reactions})

@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")