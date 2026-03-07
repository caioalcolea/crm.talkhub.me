"""
PIX Gateway client — communicates with the configured PIX provider
to generate QR codes and manage PIX transactions.

The gateway credentials are stored encrypted in IntegrationConnection
with connector_slug='pix_gateway'.
"""

import hashlib
import hmac
import logging
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)


def _decrypt_config(config_json: dict) -> dict:
    """Decrypt secret fields from IntegrationConnection config_json."""
    from cryptography.fernet import Fernet

    fernet_key = getattr(settings, "FERNET_KEY", None)
    if not fernet_key:
        return config_json

    f = Fernet(
        fernet_key.encode() if isinstance(fernet_key, str) else fernet_key
    )
    decrypted = dict(config_json)
    for key in ("client_secret", "api_key", "pix_key"):
        val = decrypted.get(key)
        if val and isinstance(val, str) and val.startswith("gAAAAA"):
            try:
                decrypted[key] = f.decrypt(val.encode()).decode()
            except Exception:
                logger.warning("Failed to decrypt PIX config field: %s", key)
    return decrypted


def get_pix_connection(org):
    """Get the active PIX gateway IntegrationConnection for an org."""
    from integrations.models import IntegrationConnection

    return IntegrationConnection.objects.filter(
        org=org,
        connector_slug="pix_gateway",
        is_active=True,
        is_connected=True,
    ).first()


def generate_pix_qrcode(connection, amount, description, expiration_minutes=30):
    """
    Generate a PIX QR Code via the configured gateway.

    Args:
        connection: IntegrationConnection with PIX gateway config
        amount: Decimal amount
        description: Payment description
        expiration_minutes: Minutes until QR code expires

    Returns:
        dict with pix_txid, qr_code_base64, pix_copy_paste, expires_at
        or raises PixGatewayError on failure
    """
    import base64
    from datetime import timedelta

    from django.utils import timezone

    config = _decrypt_config(connection.config_json)

    # Generate a unique txid
    pix_txid = f"TH{uuid.uuid4().hex[:30]}"

    expires_at = timezone.now() + timedelta(minutes=expiration_minutes)

    # Build EMV payload for PIX copia-e-cola
    pix_key = config.get("pix_key", "")
    merchant_name = config.get("merchant_name", "TalkHub")
    merchant_city = config.get("merchant_city", "SAO PAULO")

    pix_copy_paste = _build_emv_payload(
        pix_key=pix_key,
        amount=float(amount),
        txid=pix_txid,
        description=description,
        merchant_name=merchant_name,
        merchant_city=merchant_city,
    )

    # Generate QR code image as base64 PNG
    qr_code_base64 = _generate_qr_image(pix_copy_paste)

    return {
        "pix_txid": pix_txid,
        "qr_code_base64": qr_code_base64,
        "pix_copy_paste": pix_copy_paste,
        "expires_at": expires_at,
    }


def verify_webhook_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """Verify webhook payload signature using HMAC-SHA256."""
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# EMV Payload Builder (PIX Copia-e-Cola)
# ---------------------------------------------------------------------------


def _tlv(tag: str, value: str) -> str:
    """Build a TLV (Tag-Length-Value) string for EMV."""
    length = str(len(value)).zfill(2)
    return f"{tag}{length}{value}"


def _build_emv_payload(
    pix_key: str,
    amount: float,
    txid: str,
    description: str,
    merchant_name: str = "TalkHub",
    merchant_city: str = "SAO PAULO",
) -> str:
    """
    Build a PIX EMV payload string (BR Code / copia-e-cola format).

    Based on the EMV QRCPS-MPM specification for PIX.
    """
    import binascii

    # Payload Format Indicator
    payload = _tlv("00", "01")

    # Merchant Account Information (tag 26)
    gui = _tlv("00", "br.gov.bcb.pix")
    key = _tlv("01", pix_key)
    desc = _tlv("02", description[:25]) if description else ""
    mai = _tlv("26", gui + key + desc)
    payload += mai

    # Merchant Category Code
    payload += _tlv("52", "0000")

    # Transaction Currency (986 = BRL)
    payload += _tlv("53", "986")

    # Transaction Amount
    if amount > 0:
        payload += _tlv("54", f"{amount:.2f}")

    # Country Code
    payload += _tlv("58", "BR")

    # Merchant Name
    payload += _tlv("59", merchant_name[:25])

    # Merchant City
    payload += _tlv("60", merchant_city[:15])

    # Additional Data Field (tag 62) — txid
    txid_tlv = _tlv("05", txid[:25])
    payload += _tlv("62", txid_tlv)

    # CRC placeholder (tag 63, length 04)
    payload += "6304"

    # Calculate CRC16-CCITT
    crc = _crc16_ccitt(payload.encode())
    payload += crc.upper()

    return payload


def _crc16_ccitt(data: bytes) -> str:
    """Calculate CRC16-CCITT for EMV payload."""
    crc = 0xFFFF
    polynomial = 0x1021
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _generate_qr_image(data: str) -> str:
    """Generate a QR code PNG image as base64 string.

    Uses segno library if available, otherwise returns empty string.
    """
    import base64
    import io

    try:
        import segno

        qr = segno.make(data, error="M")
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=8, border=2)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode()
    except ImportError:
        logger.warning(
            "segno library not installed — QR code generation disabled. "
            "Install with: pip install segno"
        )
        return ""


class PixGatewayError(Exception):
    """Raised when PIX gateway communication fails."""

    pass
