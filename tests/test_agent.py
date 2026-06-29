from src.planner import Intent, classify_intent
from src.memory import LongTermMemoryStore


def test_planner_detecta_reporte():
    plan = classify_intent("Genera un reporte ejecutivo sobre seguridad")
    assert plan.intent == Intent.SOLICITUD_REPORTE
    assert plan.generate_report is True


def test_planner_detecta_consulta_tecnica():
    plan = classify_intent("Como funciona un inversor fotovoltaico?")
    assert plan.intent == Intent.CONSULTA_TECNICA
    assert plan.use_documents is True


def test_planner_detecta_informacion_insuficiente():
    plan = classify_intent("")
    assert plan.intent == Intent.INFORMACION_INSUFICIENTE
    assert plan.ask_clarification is True


def test_memoria_guarda_interaccion(tmp_path):
    memory_path = tmp_path / "memory.json"
    memory = LongTermMemoryStore(str(memory_path))

    memory.save_interaction("pregunta", "respuesta", "consulta_simple")

    stored = memory.load()
    assert len(stored) == 1
    assert stored[0]["question"] == "pregunta"
    assert stored[0]["intent"] == "consulta_simple"