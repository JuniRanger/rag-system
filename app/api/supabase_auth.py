from fastapi import Header, HTTPException

from app.core.config import settings
from app.core.logger import logger


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret")):
    if not settings.SUPABASE_WEBHOOK_SECRET:
        logger.warning("SUPABASE_WEBHOOK_SECRET no configurado — webhook sin autenticación")
        return

    if x_webhook_secret != settings.SUPABASE_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Webhook secret inválido")


def verify_sync_secret(x_sync_secret: str | None = Header(default=None, alias="X-Sync-Secret")):
    if not settings.SUPABASE_SYNC_SECRET:
        return

    if x_sync_secret != settings.SUPABASE_SYNC_SECRET:
        raise HTTPException(status_code=401, detail="Sync secret inválido")
