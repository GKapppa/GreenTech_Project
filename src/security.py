import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
API_KEY_REGEX = re.compile(
    r"(?:api_key|password|secret|token|key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]",
    re.IGNORECASE,
)

PROMPT_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignora las instrucciones anteriores",
    "system prompt",
    "dan mode",
    "jailbreak",
    "ignora las reglas",
    "eres ahora",
    "actúa como",
    "ignore rules",
    "bypass",
    "forget all instructions",
    "new instructions",
]

RISK_KEYWORDS = [
    "seguridad",
    "electric",
    "voltaje",
    "corriente",
    "tensión",
    "altura",
    "techo",
    "bateria",
    "riesgo",
    "accidente",
    "epp",
    "proteger",
    "peligro",
    "instalacion",
    "cable",
    "conexion",
    "panel solar",
    "inversor",
    "mppt",
]

SAFETY_WARNING = (
    "**ADVERTENCIA DE SEGURIDAD ELECTRICA Y TRABAJO EN ALTURA:** "
    "El trabajo con sistemas fotovoltaicos conlleva riesgos graves de electrocucion y caidas. "
    "Es obligatorio el uso de Equipo de Proteccion Personal adecuado (EPP: casco, guantes clase 00/0, "
    "zapatos dielectricos, arnes y linea de vida) y seguir estrictamente los protocolos descritos en "
    "los manuales de GreenTech. No realice maniobras sin supervision o certificacion tecnica.\n\n"
)

COMPLIANCE_INFO = """
MARCO NORMATIVO IMPLEMENTADO:
- Ley 19.628 de Chile (Proteccion de la Vida Privada): Datos personales identificados son 
  enmascarados antes de ser procesados por el LLM externo.
- GDPR (UE) / LGPD (Brasil): Principios de minimizacion de datos aplicados.
- NIST AI Risk Management Framework: Sistema de guardrails eticos implementado.

POLITICA DE RETENCION DE DATOS:
- Logs de observabilidad: maximo 90 dias, luego se eliminan automaticamente.
- Memoria de conversaciones: no persiste datos personales, solo texto sanitizado.
- Backups: cifrados con AES-256.

AUDITORIA:
- Todo acceso es loggeado con timestamp UTC y session ID.
- Los logs de seguridad son inmutables (append-only).
"""


def mask_pii(text: str) -> str:
    """Reemplaza correos electronicos, telefonos y credenciales en el texto."""
    if not text:
        return text
    masked = EMAIL_REGEX.sub("[EMAIL_MASKED]", text)
    masked = PHONE_REGEX.sub("[PHONE_MASKED]", masked)
    masked = API_KEY_REGEX.sub("[CREDENTIAL_MASKED]", masked)
    return masked


def is_prompt_injection(text: str) -> bool:
    """Verifica si la consulta contiene patrones sospechosos de inyeccion de prompt."""
    if not text:
        return False
    normalized = text.lower()
    return any(keyword in normalized for keyword in PROMPT_INJECTION_KEYWORDS)


def needs_safety_warning(text: str) -> bool:
    """Determina si la consulta involucra riesgos de seguridad fisica."""
    if not text:
        return False
    normalized = text.lower()
    return any(keyword in normalized for keyword in RISK_KEYWORDS)


def get_client_ip(request_headers: dict | None = None) -> str:
    """Extrae la direccion IP del cliente desde las cabeceras HTTP."""
    if not request_headers:
        return "unknown"

    for header_name in ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]:
        if header_name in request_headers:
            ip = request_headers[header_name]
            if isinstance(ip, str):
                return ip.split(",")[0].strip()
    return "unknown"


def audit_access(
    question: str,
    answer: str,
    session_id: str,
    intent: str,
    status: str,
    client_ip: str = "unknown",
) -> None:
    """Registra un acceso para auditoria de compliance."""
    audit_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "intent": intent,
        "status": status,
        "client_ip": client_ip,
        "query_length": len(question),
        "response_length": len(answer),
        "query_masked": mask_pii(question)[:150],
        "pii_detected": bool(
            EMAIL_REGEX.search(question)
            or PHONE_REGEX.search(question)
            or API_KEY_REGEX.search(question)
        ),
    }

    audit_path = Path("data/logs/audit_logs.jsonl")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")


def log_consent(
    session_id: str,
    user_id: str | None = None,
    purpose: str = "induccion_tecnica",
) -> None:
    """Registra el consentimiento del usuario para el procesamiento de datos."""
    consent_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_id": user_id or "anonymous",
        "purpose": purpose,
        "consent_given": True,
        "consent_version": "1.0",
    }

    consent_path = Path("data/logs/consent_logs.jsonl")
    with open(consent_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(consent_record, ensure_ascii=False) + "\n")


def load_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Carga los registros de auditoria mas recientes."""
    audit_path = Path("data/logs/audit_logs.jsonl")
    if not audit_path.exists():
        return []

    logs = []
    with open(audit_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[-limit:]:
        if line.strip():
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    return list(reversed(logs))


def load_consent_logs(limit: int = 50) -> list[dict[str, Any]]:
    """Carga los registros de consentimiento mas recientes."""
    consent_path = Path("data/logs/consent_logs.jsonl")
    if not consent_path.exists():
        return []

    logs = []
    with open(consent_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[-limit:]:
        if line.strip():
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    return list(reversed(logs))


def apply_safety_guardrails(question: str) -> tuple[str, bool, str | None]:
    """
    Evalua la consulta del usuario aplicando los filtros de seguridad.

    Retorna:
        - consulta_sanitizada (str): Consulta con PII enmascarada.
        - es_segura (bool): True si pasa el filtro de inyeccion, False de lo contrario.
        - mensaje_error (str | None): Mensaje a mostrar si es bloqueada, o None.
    """
    sanitized = mask_pii(question)

    if is_prompt_injection(sanitized):
        return sanitized, False, (
            "**Acceso Restringido:** Se ha detectado una consulta que viola las politicas "
            "de uso responsable e integridad del sistema de GreenTech. "
            "Esta interaccion ha sido bloqueada y registrada por seguridad."
        )

    return sanitized, True, None


def sanitize_output(text: str) -> str:
    """Aplica sanitizacion adicional a la salida del LLM."""
    if not text:
        return text

    sanitized = mask_pii(text)

    sensitive_patterns = [
        (r"\d{8,}", "[NUMERO_ID_MASKED]"),
        (r"\b\d{2}\.\d{3}\.\d{3}-[kK]\b", "[RUT_MASKED]"),
    ]

    for pattern, replacement in sensitive_patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized
