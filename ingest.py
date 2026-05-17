import os

import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient


load_dotenv()

DB_NAME = "GreenTech_DB"
COLLECTION_NAME = "manuals_vectors"
INDEX_NAME = "vector_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Eres el Mentor Senior de Ingenieria en GreenTech. Tu mision es capacitar a nuevos integrantes usando manuales tecnicos oficiales.

ESTILO DE MENTORIA:
1. Rigor tecnico: usa conceptos como irradiancia, MPPT, inversores, baterias, protecciones y estructura fotovoltaica cuando el contexto lo respalde.
2. Seguridad primero: si la pregunta implica riesgo electrico, trabajo en altura o manipulacion de equipos, inicia con una advertencia breve.
3. Formato educativo: responde con pasos, listas o secciones cortas cuando ayude a comprender.
4. Basado en datos: responde solo con la informacion de los manuales tecnicos proporcionados.
5. Sin inventos: si el tema no esta cubierto en el contexto, indica que debe validarse con un supervisor o documentacion oficial adicional."""

SIDEBAR_QUESTIONS = {
    "Fundamentos Fotovoltaicos": "Explicame como funcionan los paneles solares y que es el efecto fotoelectrico.",
    "Protocolos de Seguridad": "Cuales son las reglas principales de seguridad electrica para trabajar con sistemas fotovoltaicos?",
    "Sistemas de Almacenamiento": "Como se gestionan las baterias y el ciclo de carga en un sistema fotovoltaico?",
}


def get_missing_environment_variables() -> list[str]:
    required_variables = ["GROQ_API_KEY", "MONGODB_ATLAS_URI"]
    return [name for name in required_variables if not os.getenv(name)]


@st.cache_resource(show_spinner=False)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


@st.cache_resource(show_spinner=False)
def get_llm(groq_api_key: str) -> ChatGroq:
    return ChatGroq(
        temperature=0.2,
        groq_api_key=groq_api_key,
        model_name=GROQ_MODEL,
    )


@st.cache_resource(show_spinner=False)
def get_vector_search(mongodb_uri: str) -> MongoDBAtlasVectorSearch:
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client[DB_NAME][COLLECTION_NAME]

    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=get_embeddings(),
        index_name=INDEX_NAME,
    )


def build_messages(question: str, context: str, memory: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "MEMORIA RECIENTE DE LA SESION:\n"
                f"{memory}\n\n"
                "MANUALES TECNICOS DE APOYO:\n"
                f"{context}\n\n"
                "PREGUNTA DEL APRENDIZ:\n"
                f"{question}"
            ),
        },
    ]


def search_context(vector_search: MongoDBAtlasVectorSearch, question: str) -> str:
    docs = vector_search.similarity_search(question, k=4)
    return "\n\n".join(doc.page_content for doc in docs)


def answer_question(question: str, vector_search: MongoDBAtlasVectorSearch, llm: ChatGroq) -> str:
    context = search_context(vector_search, question)

    if not context.strip():
        return (
            "No encontre informacion suficiente en los manuales cargados para responder con rigor. "
            "Valida este tema con un supervisor humano o con documentacion tecnica oficial adicional."
        )

    response = llm.invoke(build_messages(question, context, get_memory_tool()))
    return response.content


def search_documents_tool(question: str, vector_search: MongoDBAtlasVectorSearch) -> str:
    """Busca fragmentos relevantes en el vector store de MongoDB Atlas."""
    return search_context(vector_search, question)


def get_memory_tool() -> str:
    """Recupera el historial de la sesion actual de Streamlit."""
    messages = st.session_state.get("messages", [])
    if not messages:
        return "No hay mensajes previos en esta sesion."

    return "\n".join(f"{message['role']}: {message['content']}" for message in messages[-6:])


def save_memory_tool(role: str, content: str) -> None:
    """Guarda un mensaje en la memoria corta de la conversacion."""
    st.session_state.messages.append({"role": role, "content": content})


def generate_report_tool(question: str, context: str, llm: ChatGroq) -> str:
    """Genera un reporte ejecutivo usando la misma base documental recuperada."""
    report_prompt = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
                f"SOLICITUD:\n{question}"
            ),
        },
    ]
    return llm.invoke(report_prompt).content


def is_report_request(question: str) -> bool:
    report_keywords = ["reporte", "informe", "resumen ejecutivo", "documento ejecutivo"]
    normalized_question = question.lower()
    return any(keyword in normalized_question for keyword in report_keywords)


st.set_page_config(page_title="Academia GreenTech", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

st.title("GreenTech Academy: Mentor de Induccion")
st.markdown(
    """
---
**Bienvenido al equipo.** Soy tu Mentor IA para consultar los manuales tecnicos de GreenTech mediante RAG.
"""
)

missing_variables = get_missing_environment_variables()
if missing_variables:
    st.error(
        "Faltan variables de entorno requeridas en `.env`: "
        + ", ".join(missing_variables)
        + ". Revisa `.env.example` antes de ejecutar la aplicacion."
    )
    st.stop()

try:
    vector_search = get_vector_search(os.environ["MONGODB_ATLAS_URI"])
    llm = get_llm(os.environ["GROQ_API_KEY"])
except Exception as exc:
    st.error("No fue posible inicializar el motor RAG. Revisa MongoDB Atlas, el indice vectorial y las credenciales.")
    st.exception(exc)
    st.stop()

with st.sidebar:
    st.header("Modulos de aprendizaje")
    st.info("Selecciona un tema para generar una consulta guiada.")

    for label, question in SIDEBAR_QUESTIONS.items():
        if st.button(label):
            st.session_state.pending_prompt = question
            st.rerun()

    if st.button("Reiniciar tutoria"):
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

typed_prompt = st.chat_input("Preguntame una duda tecnica sobre los manuales...")
prompt = typed_prompt or st.session_state.pending_prompt
st.session_state.pending_prompt = None

if prompt:
    save_memory_tool("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en los manuales tecnicos..."):
            try:
                context = search_documents_tool(prompt, vector_search)
                if is_report_request(prompt):
                    final_answer = generate_report_tool(prompt, context, llm)
                elif not context.strip():
                    final_answer = (
                        "No encontre informacion suficiente en los manuales cargados para responder con rigor. "
                        "Valida este tema con un supervisor humano o con documentacion tecnica oficial adicional."
                    )
                else:
                    final_answer = llm.invoke(build_messages(prompt, context, get_memory_tool())).content
            except Exception as exc:
                final_answer = (
                    "Ocurrio un problema al consultar los manuales o generar la respuesta. "
                    "Revisa la conexion a MongoDB Atlas, el indice vectorial y la API key de Groq."
                )
                st.exception(exc)

        st.markdown(final_answer)
        save_memory_tool("assistant", final_answer)
