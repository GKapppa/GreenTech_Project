SYSTEM_PROMPT = """Eres el Mentor Senior de Ingenieria en GreenTech. Tu mision es capacitar a nuevos integrantes usando manuales tecnicos oficiales.

ESTILO DE MENTORIA:
1. Rigor tecnico: usa conceptos como irradiancia, MPPT, inversores, baterias, protecciones y estructura fotovoltaica cuando el contexto lo respalde.
2. Seguridad primero: si la pregunta implica riesgo electrico, trabajo en altura o manipulacion de equipos, inicia con una advertencia breve.
3. Formato educativo: responde con pasos, listas o secciones cortas cuando ayude a comprender.
4. Basado en datos: responde solo con la informacion de los manuales tecnicos proporcionados.
5. Sin inventos: si el tema no esta cubierto en el contexto, indica que debe validarse con un supervisor o documentacion oficial adicional."""


def build_simple_answer_messages(
    question: str,
    short_memory: str,
    long_memory: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Responde de forma breve y directa. No inventes datos tecnicos.\n\n"
                f"MEMORIA CORTA:\n{short_memory}\n\n"
                f"MEMORIA LARGA:\n{long_memory}\n\n"
                f"PREGUNTA:\n{question}"
            ),
        },
    ]


def build_rag_messages(
    question: str,
    context: str,
    short_memory: str,
    long_memory: str,
    intent: str,
    reason: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"INTENCION DETECTADA: {intent}\n"
                f"MOTIVO DEL PLAN: {reason}\n\n"
                f"MEMORIA CORTA:\n{short_memory}\n\n"
                f"MEMORIA LARGA:\n{long_memory}\n\n"
                f"MANUALES TECNICOS DE APOYO:\n{context}\n\n"
                f"PREGUNTA DEL APRENDIZ:\n{question}"
            ),
        },
    ]


def build_report_messages(
    topic: str,
    context: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Genera un reporte ejecutivo breve y tecnico para GreenTech.\n\n"
                "Usa esta estructura:\n"
                "1. Resumen ejecutivo\n"
                "2. Hallazgos tecnicos\n"
                "3. Riesgos o consideraciones de seguridad\n"
                "4. Recomendaciones\n\n"
                f"CONTEXTO DOCUMENTAL:\n{context}\n\n"
                f"SOLICITUD:\n{topic}"
            ),
        },
    ]
