"""Gestion de l'authentification : création et vérification des tokens JWT
utilisés pour identifier un utilisateur connecté (pseudo + mot de passe)."""

import datetime
import os

import jwt

# Clé secrète utilisée pour signer les tokens JWT — À DÉFINIR en production
# via la variable d'environnement JWT_SECRET (ex. sur Railway), sinon tous
# les tokens deviennent invalides à chaque redéploiement et un secret
# prévisible est utilisé, ce qui est dangereux.
JWT_SECRET = os.environ.get("JWT_SECRET", "changeme-en-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30


def create_token(user_id: int, pseudo: str) -> str:
    """Génère un token JWT signé, valable 30 jours, contenant l'id et le
    pseudo de l'utilisateur."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "pseudo": pseudo,
        "iat": now,
        "exp": now + datetime.timedelta(days=JWT_EXPIRATION_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Vérifie et décode un token JWT. Renvoie None s'il est invalide,
    expiré, ou mal signé."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_token_from_header(authorization: str | None) -> str | None:
    """Extrait le token d'un en-tête 'Authorization: Bearer <token>'."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()
