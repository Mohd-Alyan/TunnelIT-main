import secrets
import string
import uuid
from relay.config import settings

def generate_tunnel_id() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(settings.TUNNEL_ID_LENGTH))

def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"

def get_public_url(tunnel_id: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip('/')
    return f"{base}/t/{tunnel_id}"
