
#explication: ce fichier est le fichier qui permet d'envoyer les notifications push
import base64#explication: ce fichier est le fichier qui permet d'encoder en base64
import json#explication: ce fichier est le fichier qui permet de manipuler des données JSON
import os#explication: ce fichier est le fichier qui permet de manipuler des chemins de fichiers
from typing import Iterable#explication: ce fichier est le fichier qui permet de manipuler des itérables

from cryptography.hazmat.primitives import serialization#explication: ce fichier est le fichier qui permet de manipuler des clés de chiffrement
from py_vapid import Vapid01
from pywebpush import WebPushException, webpush
#explication: ce fichier est le fichier qui permet d'envoyer les notifications push
# Chemin du fichier contenant la clé privée VAPID, surchargeable via la
# variable d'environnement VAPID_KEY_PATH — à définir vers un volume
# persistant en production (ex. /data/vapid_private.pem sur Railway),
# sinon ce fichier est perdu (et les abonnements aux notifications
# invalidés) à chaque redéploiement du service.
VAPID_PRIVATE_KEY_FILE = os.environ.get("VAPID_KEY_PATH", "vapid_private.pem")
# À personnaliser si tu veux : email de contact requis par la norme VAPID
# (les navigateurs ne l'affichent jamais à l'utilisateur).
VAPID_CLAIMS_EMAIL = "mailto:contact@example.com"

#explication: ce fichier est le fichier qui permet de charger la paire de clés VAPID
def get_vapid_public_key(private_key_path: str = VAPID_PRIVATE_KEY_FILE) -> str:
    """Charge la paire de clés VAPID (la génère au tout premier appel si le
    fichier n'existe pas encore) et renvoie la clé publique encodée en
    base64url, telle qu'attendue par pushManager.subscribe() côté navigateur."""

    parent_dir = os.path.dirname(private_key_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    vapid = Vapid01.from_file(private_key_path)
    raw_public = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw_public).rstrip(b"=").decode()


#explication: ce fichier est le fichier qui permet d'envoyer une notification à un seul abonné
def send_push(
    subscription_info: dict,
    payload: dict,
    private_key_path: str = VAPID_PRIVATE_KEY_FILE,
) -> bool:
    """Envoie une notification à un seul abonné. Renvoie False si l'abonnement
    n'est plus valide (navigateur désinstallé, permission révoquée, etc.)."""
#explication: ce fichier est le fichier qui permet d'envoyer une notification à un seul abonné
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=private_key_path,
            vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
        )
        return True
    except WebPushException:
        return False


#explication: ce fichier est le fichier qui permet d'envoyer une notification à tous les abonnés
def send_push_to_all(
    subscriptions: Iterable[dict],
    payload: dict,
    private_key_path: str = VAPID_PRIVATE_KEY_FILE,
) -> list[str]:
    """Envoie à tous les abonnés. Renvoie la liste des endpoints devenus
    invalides, à supprimer de la base."""

    dead_endpoints = []
    for sub in subscriptions:
        if not send_push(sub, payload, private_key_path):
            dead_endpoints.append(sub["endpoint"])
    return dead_endpoints