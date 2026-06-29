from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    CONSULTA_SIMPLE = "consulta_simple"
    CONSULTA_TECNICA = "consulta_tecnica"
    SOLICITUD_REPORTE = "solicitud_reporte"
    CONTINUIDAD_CONTEXTO = "continuidad_contexto"
    INFORMACION_INSUFICIENTE = "informacion_insuficiente"


@dataclass
class Plan:
    intent: Intent
    reason: str
    use_documents: bool
    use_memory: bool
    generate_report: bool
    ask_clarification: bool


REPORT_KEYWORDS = ["reporte", "informe", "resumen ejecutivo", "documento ejecutivo"]
CONTEXT_KEYWORDS = ["eso", "lo anterior", "anterior", "como dijiste", "segun lo hablado", "continua"]
TECHNICAL_KEYWORDS = [
    "fotovoltaico",
    "panel",
    "inversor",
    "bateria",
    "mppt",
    "irradiancia",
    "corriente",
    "voltaje",
    "seguridad",
    "instalacion",
    "sistema",
    "energia",
    "proteccion",
    "carga",
]
SIMPLE_KEYWORDS = ["hola", "gracias", "quien eres", "que haces", "ayuda"]


def classify_intent(question: str, has_memory: bool = False) -> Plan:
    normalized_question = question.strip().lower()

    if not normalized_question or len(normalized_question.split()) < 2:
        return Plan(
            intent=Intent.INFORMACION_INSUFICIENTE,
            reason="La pregunta es demasiado breve para responder con seguridad.",
            use_documents=False,
            use_memory=False,
            generate_report=False,
            ask_clarification=True,
        )

    if any(keyword in normalized_question for keyword in REPORT_KEYWORDS):
        return Plan(
            intent=Intent.SOLICITUD_REPORTE,
            reason="El usuario pide un reporte o informe.",
            use_documents=True,
            use_memory=True,
            generate_report=True,
            ask_clarification=False,
        )

    if has_memory and any(keyword in normalized_question for keyword in CONTEXT_KEYWORDS):
        return Plan(
            intent=Intent.CONTINUIDAD_CONTEXTO,
            reason="La consulta depende de informacion mencionada antes.",
            use_documents=True,
            use_memory=True,
            generate_report=False,
            ask_clarification=False,
        )

    if any(keyword in normalized_question for keyword in TECHNICAL_KEYWORDS):
        return Plan(
            intent=Intent.CONSULTA_TECNICA,
            reason="La pregunta contiene terminos tecnicos del dominio GreenTech.",
            use_documents=True,
            use_memory=True,
            generate_report=False,
            ask_clarification=False,
        )

    if any(keyword in normalized_question for keyword in SIMPLE_KEYWORDS):
        return Plan(
            intent=Intent.CONSULTA_SIMPLE,
            reason="La pregunta puede responderse sin recuperar documentos.",
            use_documents=False,
            use_memory=True,
            generate_report=False,
            ask_clarification=False,
        )

    return Plan(
        intent=Intent.CONSULTA_TECNICA,
        reason="La consulta requiere revisar documentacion para evitar una respuesta inventada.",
        use_documents=True,
        use_memory=True,
        generate_report=False,
        ask_clarification=False,
    )
