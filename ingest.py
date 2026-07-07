import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.agent import GreenTechAgent
from src.cache import SemanticCache
from src.memory import LongTermMemoryStore
from src.observability import AnomalyDetector, ObservabilityLogger
from src.prompts import SYSTEM_PROMPT
from src.security import (
    COMPLIANCE_INFO,
    audit_access,
    load_audit_logs,
    log_consent,
)
from src.tools import GreenTechTools
from src.vectorstore import get_vector_search

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
SIDEBAR_QUESTIONS = {
    "Fundamentos Fotovoltaicos": "Explicame como funcionan los paneles solares y que es el efecto fotoelectrico.",
    "Protocolos de Seguridad": "Cuales son las reglas principales de seguridad electrica para trabajar con sistemas fotovoltaicos?",
    "Sistemas de Almacenamiento": "Como se gestionan las baterias y el ciclo de carga en un sistema fotovoltaico?",
}


def get_missing_environment_variables() -> list[str]:
    required_variables = ["GROQ_API_KEY", "MONGODB_ATLAS_URI"]
    return [name for name in required_variables if not os.getenv(name)]


@st.cache_resource(show_spinner=False)
def get_llm(groq_api_key: str) -> ChatGroq:
    return ChatGroq(
        temperature=0.2,
        groq_api_key=groq_api_key,
        model_name=GROQ_MODEL,
    )


@st.cache_resource(show_spinner=False)
def get_cached_vector_search(mongodb_uri: str):
    return get_vector_search(mongodb_uri)


st.set_page_config(
    page_title="Academia GreenTech - Observabilidad",
    page_icon="☀️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f9fbf9;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    h1, h2, h3 {
        color: #1b5e20 !important;
        font-weight: 700 !important;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(46, 125, 50, 0.15);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        backdrop-filter: blur(10px);
        margin-bottom: 10px;
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.08);
    }
    .metric-title {
        font-size: 14px;
        color: #555555;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 28px;
        color: #2e7d32;
        font-weight: 700;
    }
    .metric-subtitle {
        font-size: 11px;
        color: #888888;
        margin-top: 5px;
    }
    .safety-alert {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 15px;
        color: #e65100;
        font-weight: 500;
    }
    .css-1d391kg {
        background-color: #f1f8e9 !important;
    }
    .anomaly-alert {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .recommendation-box {
        background-color: #e8f5e9;
        border-left: 5px solid #4caf50;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"

if "semantic_cache" not in st.session_state:
    st.session_state.semantic_cache = SemanticCache()

missing_variables = get_missing_environment_variables()
if missing_variables:
    st.error(
        "Faltan variables de entorno requeridas en `.env`: "
        + ", ".join(missing_variables)
        + ". Revisa `.env.example` antes de ejecutar la aplicacion."
    )
    st.stop()

try:
    vector_search = get_cached_vector_search(os.environ["MONGODB_ATLAS_URI"])
    llm = get_llm(os.environ["GROQ_API_KEY"])
    greentech_tools = GreenTechTools(
        vector_search=vector_search,
        llm=llm,
        memory=st.session_state.messages,
        system_prompt=SYSTEM_PROMPT,
    )
    obs_logger = ObservabilityLogger()
    agent = GreenTechAgent(
        tools=greentech_tools,
        llm=llm,
        memory_store=LongTermMemoryStore(),
        system_prompt=SYSTEM_PROMPT,
        observability_logger=obs_logger,
    )
except Exception as exc:
    st.error("No fue posible inicializar el motor RAG. Revisa MongoDB Atlas, el indice vectorial y las credenciales.")
    st.exception(exc)
    st.stop()


with st.sidebar:
    st.image(
        "https://img.icons8.com/external-flat-icons-inspirational-tuts/100/external-solar-panel-alternative-energy-flat-icons-inspirational-tuts.png",
        width=100,
    )
    st.title("GreenTech Academy")
    st.markdown("---")
    st.header("Modulos de aprendizaje")
    st.info("Selecciona un tema para generar una consulta guiada.")

    for label, question in SIDEBAR_QUESTIONS.items():
        if st.button(label, use_container_width=True):
            st.session_state.pending_prompt = question
            st.rerun()

    if st.button("Reiniciar tutoria", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()
    st.markdown("---")
    st.header("Preguntas sugeridas")
    st.markdown("Haz click en cualquier pregunta para probarla:")

    suggested_questions = [
        "Explicame el efecto fotoelectrico",
        "Como funciona un panel solar?",
        "Que es el MPPT en un regulador?",
        "Cuales son las medidas de seguridad electrica?",
        "Diferencia entre inversores string y microinversores",
        "Como calcular el tamaño de un sistema fotovoltaico?",
        "Que es el netbilling?",
        "Explícame el efecto fotoelectrico y las celulas de silicio",
    ]

    for q in suggested_questions:
        if st.button(q, use_container_width=True):
            st.session_state.pending_prompt = q
            st.rerun()

    st.markdown("---")

    st.caption(f"Session ID: `{st.session_state.session_id}`")

    cache_stats = st.session_state.semantic_cache.get_stats()
    with st.expander("Estadisticas Cache Semantico"):
        st.write(f"Entradas en cache: {cache_stats.get('size', 0)}")
        st.write(f"Total de hits: {cache_stats.get('total_hits', 0)}")
        st.write(f"Latencia ahorrada: {cache_stats.get('estimated_latency_savings_ms', 0):.0f} ms")
        st.write(f"Tasa de acierto (ultimas 10): {cache_stats.get('hit_rate_last_10', 0)*100:.1f}%")

    log_consent(st.session_state.session_id, purpose="induccion_tecnica_greentech")


tab_chat, tab_dashboard, tab_audit = st.tabs([
    "Tutoria Interactiva (Chat)",
    "Dashboard de Observabilidad",
    "Auditoria y Compliance",
])

with tab_chat:
    st.title("Mentor de Induccion Inteligente")
    st.markdown(
        """
        Bienvenido al portal de capacitacion de GreenTech. Soy tu Mentor de IA especializado.
        Puedes realizar preguntas tecnicas basadas en los manuales de instalacion solar, seguridad fisica e inversores.
        """
    )
    st.markdown("---")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    typed_prompt = st.chat_input("Preguntame una duda tecnica sobre los manuales...")
    prompt = typed_prompt or st.session_state.pending_prompt
    st.session_state.pending_prompt = None

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        cached_answer, cache_meta = st.session_state.semantic_cache.get(prompt)
        agent_response = None
        current_intent = "unknown"

        if cached_answer and cache_meta.get("cache_hit"):
            final_answer = cached_answer
            current_intent = cache_meta.get("cached_intent", "unknown")
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            with st.chat_message("assistant"):
                st.markdown(final_answer)
                st.caption(f"Respuesta desde cache (similitud: {cache_meta.get('similarity', 0)*100:.1f}%)")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Buscando en los manuales tecnicos..."):
                    agent_response = None
                    try:
                        agent_response = agent.run(prompt)
                        final_answer = agent_response.answer

                        if agent_response and agent_response.plan:
                            current_intent = agent_response.plan.intent.value
                            cache_intent = current_intent
                        else:
                            cache_intent = "unknown"
                            current_intent = "unknown"

                        tokens_data = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

                        st.session_state.semantic_cache.add(
                            query=prompt,
                            answer=final_answer,
                            intent=cache_intent,
                            latency=0.5,
                            tokens_used=tokens_data.get("total_tokens", 0),
                            relevance_score=0.7,
                        )
                    except Exception as exc:
                        final_answer = (
                            "Ocurrio un problema al consultar los manuales o generar la respuesta. "
                            "Revisa la conexion a MongoDB Atlas, el indice vectorial y la API key de Groq."
                        )
                        st.exception(exc)

            st.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})

            if agent_response and getattr(agent_response, "security_alert", False):
                st.warning("Esta consulta involucra riesgos de seguridad fisica y ha activado el protocolo de advertencia etica de GreenTech.")

            if agent_response:
                with st.expander("Proceso de decision y trazabilidad del agente"):
                    st.write(f"**Intencion Detectada:** `{agent_response.plan.intent.value}`")
                    st.write(f"**Justificacion de Ruta:** {agent_response.plan.reason}")
                    st.write(f"**Documentos Consultados:** {'Si (Busqueda Semantica activa)' if agent_response.plan.use_documents else 'No'}")
                    st.write(f"**Memoria Consultada:** {'Si (Memoria corta y larga activas)' if agent_response.plan.use_memory else 'No'}")

        audit_access(
            question=prompt,
            answer=final_answer,
            session_id=st.session_state.session_id,
            intent=current_intent,
            status="success",
        )


with tab_dashboard:
    st.title("Panel de Observabilidad y Trazabilidad")
    st.markdown(
        """
        Visualizacion en tiempo real del comportamiento del agente, el consumo de recursos,
        los tiempos de respuesta (latencias) y las auditorias de seguridad en entornos de produccion.
        """
    )
    st.markdown("---")

    logs = obs_logger.load_logs()

    if not logs:
        st.warning("No hay registros de observabilidad disponibles. Interactua con el chat para registrar datos.")
    else:
        df = pd.DataFrame(logs)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        for lat_key in ["planner", "retrieval", "generation", "security", "total"]:
            df[f"latency_{lat_key}"] = df["latencies"].apply(
                lambda l: l.get(lat_key, 0.0) if isinstance(l, dict) else 0.0
            )

        for tok_key in ["input_tokens", "output_tokens", "total_tokens"]:
            df[tok_key] = df["tokens"].apply(
                lambda t: t.get(tok_key, 0) if isinstance(t, dict) else 0
            )

        detector = AnomalyDetector(logs)
        summary = detector.generate_summary()

        kpi_total_queries = len(df)
        kpi_avg_latency = df["latency_total"].mean()
        kpi_success_rate = (df["status"] == "success").sum() / kpi_total_queries * 100
        kpi_total_cost = df["estimated_cost_usd"].sum()

        df_rag = df[df["intent"].isin(["consulta_tecnica", "solicitud_reporte"]) & (df["status"] == "success")]
        kpi_avg_relevance = df_rag["relevance_score"].mean() * 100 if not df_rag.empty else 0.0

        kpi_security_alerts = int(
            df["security_alert"].sum() + (df["status"] == "security_block").sum()
        )

        percentiles = detector.calculate_percentiles()

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Consultas Totales</div>
                    <div class="metric-value">{kpi_total_queries}</div>
                    <div class="metric-subtitle">Interacciones registradas</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Latencia Promedio</div>
                    <div class="metric-value">{kpi_avg_latency:.2f}s</div>
                    <div class="metric-subtitle">Tiempo total de respuesta</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Tasa de Exito</div>
                    <div class="metric-value">{kpi_success_rate:.1f}%</div>
                    <div class="metric-subtitle">Peticiones exitosas</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Precision RAG</div>
                    <div class="metric-value">{kpi_avg_relevance:.1f}%</div>
                    <div class="metric-subtitle">Relevancia de recuperacion</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col5:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Alertas / Bloqueos</div>
                    <div class="metric-value">{kpi_security_alerts}</div>
                    <div class="metric-subtitle">Incidentes de seguridad</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col6:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Costo Acumulado</div>
                    <div class="metric-value">${kpi_total_cost:.5f}</div>
                    <div class="metric-subtitle">Costo estimado en USD</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Analisis de Rendimiento y Recursos")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Desglose de Latencias por Componente")
            df_sorted = df.sort_values(by="timestamp")
            lat_df = df_sorted[["timestamp", "latency_planner", "latency_retrieval", "latency_generation", "latency_security"]].copy()
            lat_df.set_index("timestamp", inplace=True)
            st.line_chart(lat_df)
            st.caption("Evolucion temporal de la latencia en segundos para cada fase del agente.")

        with col_right:
            st.subheader("Distribucion de Intenciones Clasificadas")
            intent_counts = df["intent"].value_counts().reset_index()
            intent_counts.columns = ["Intencion", "Cantidad"]
            st.bar_chart(intent_counts, x="Intencion", y="Cantidad")
            st.caption("Distribucion del tipo de intenciones clasificadas por el planner.")

        col_left2, col_right2 = st.columns(2)

        with col_left2:
            st.subheader("Consumo de Recursos: Tokens y Costo")
            df_sorted_tok = df.sort_values(by="timestamp")
            tokens_df = df_sorted_tok[["timestamp", "input_tokens", "output_tokens"]].copy()
            tokens_df.set_index("timestamp", inplace=True)
            st.area_chart(tokens_df)
            st.caption("Uso acumulado de tokens de entrada (prompt) y salida (generacion).")

        with col_right2:
            st.subheader("Relevancia Semantica de Recuperacion")
            df_rag_sorted = df_rag.sort_values(by="timestamp") if not df_rag.empty else pd.DataFrame()
            if df_rag_sorted.empty:
                st.info("No hay suficientes consultas RAG para mostrar tendencia de precision semantica.")
            else:
                rel_df = df_rag_sorted[["timestamp", "relevance_score"]].copy()
                rel_df.set_index("timestamp", inplace=True)
                st.line_chart(rel_df)
                st.caption("Similitud de coseno del embedding entre la pregunta y los documentos recuperados.")

        st.markdown("---")
        st.subheader("Analisis de Anomalias y Recomendaciones")

        recs = summary.get("recommendations", [])
        if recs:
            for rec in recs:
                st.info(rec)
        else:
            st.success("No se detectaron anomalias criticas. El sistema opera dentro de parametros normales.")

        col_anom1, col_anom2 = st.columns(2)

        with col_anom1:
            st.subheader("Percentiles de Latencia")
            if percentiles:
                perc_df = pd.DataFrame({
                    "Percentil": ["P50 (Mediana)", "P95", "P99"],
                    "Latencia (s)": [percentiles.get("p50", 0), percentiles.get("p95", 0), percentiles.get("p99", 0)],
                }).set_index("Percentil")
                st.bar_chart(perc_df)
                st.caption(f"Basado en {kpi_total_queries} muestras")

        with col_anom2:
            st.subheader("Patrones de Error por Intencion")
            error_patterns = detector.detect_error_patterns()
            if error_patterns:
                err_df = pd.DataFrame({
                    "Intencion": list(error_patterns.keys()),
                    "Errores": list(error_patterns.values()),
                }).set_index("Intencion")
                st.bar_chart(err_df)
            else:
                st.info("No se detectaron patrones de error significativos.")

        error_rates = detector.calculate_error_rate(window_size=10)
        if error_rates and len(error_rates) > 1:
            st.subheader("Tasa de Error en Ventanas Moviles")
            rate_df = pd.DataFrame(error_rates)
            rate_df = rate_df.set_index("window")
            st.line_chart(rate_df[["error_rate"]])
            st.caption("Tasa de error calculada en ventanas de 10 consultas consecutivas.")

        outliers = detector.detect_latency_outliers()
        if outliers:
            st.warning(f"Se detectaron {len(outliers)} latencias anomalas (superiores al P95)")
            st.dataframe(pd.DataFrame(outliers).head())

        st.markdown("---")
        st.subheader("Explorador de Auditoria y Trazabilidad de Logs")

        search_filter = st.text_input("Filtrar logs por texto en la pregunta...")
        status_filter = st.multiselect(
            "Filtrar por Estado:",
            options=df["status"].unique().tolist(),
            default=df["status"].unique().tolist(),
        )

        filtered_df = df.copy()
        if search_filter:
            filtered_df = filtered_df[
                filtered_df["question"].str.contains(search_filter, case=False, na=False)
            ]
        filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]

        display_cols = [
            "timestamp", "question", "intent", "latency_total",
            "total_tokens", "estimated_cost_usd", "relevance_score",
            "quality_score", "status", "security_alert",
        ]
        display_cols = [c for c in display_cols if c in filtered_df.columns]

        display_df = filtered_df[display_cols].copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        col_labels = {
            "timestamp": "Fecha/Hora (UTC)",
            "question": "Pregunta",
            "intent": "Intencion",
            "latency_total": "Latencia Total (s)",
            "total_tokens": "Tokens Usados",
            "estimated_cost_usd": "Costo (USD)",
            "relevance_score": "Precision Semantica",
            "quality_score": "Calidad Respuesta",
            "status": "Estado",
            "security_alert": "Alerta Seguridad",
        }
        display_df.columns = [col_labels.get(c, c) for c in display_df.columns]

        st.dataframe(display_df, use_container_width=True)
        st.caption(f"Mostrando {len(display_df)} de {len(df)} registros.")

        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Descargar logs como CSV",
            data=csv_data,
            file_name="observability_logs.csv",
            mime="text/csv",
        )


with tab_audit:
    st.title("Auditoria y Compliance")
    st.markdown("### Registro de Accesos y Auditoria")
    st.markdown(
        """
        Esta seccion permite auditar todos los accesos al sistema, incluyendo
        direcciones IP, consultas realizadas y deteccion de PII.
        """
    )

    audit_logs = load_audit_logs(limit=100)

    if not audit_logs:
        st.info("No hay registros de auditoria disponibles.")
    else:
        audit_df = pd.DataFrame(audit_logs)
        if not audit_df.empty:
            audit_df["timestamp"] = pd.to_datetime(audit_df["timestamp"])
            audit_df["timestamp"] = audit_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

            st.dataframe(audit_df, use_container_width=True)
            st.caption(f"Total de accesos registrados: {len(audit_df)}")

            pii_detected_count = audit_df["pii_detected"].sum() if "pii_detected" in audit_df.columns else 0
            if pii_detected_count > 0:
                st.warning(f"Se detectaron {int(pii_detected_count)} consultas con PII que fueron enmascaradas.")

        else:
            st.info("No hay registros de auditoria para mostrar.")

    st.markdown("---")
    st.markdown("### Marco Normativo y Politicas de Retention")

    st.markdown(COMPLIANCE_INFO)

    st.markdown("---")
    st.markdown("### Informacion del Sistema")

    sys_info = {
        "Sesion activa": st.session_state.session_id,
        "Modelo LLM": GROQ_MODEL,
        "Proveedor": "Groq",
        "Base vectorial": "MongoDB Atlas",
        "Framework agente": "LangChain",
    }

    for key, value in sys_info.items():
        st.write(f"**{key}:** {value}")
