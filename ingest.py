import streamlit as st
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

# 1. CARGAMOS CONFIGURACION Y VARIABLES
# Traemos la API KEY y la URL de mongo desde el .env que ya hicimos.
load_dotenv()


DB_NAME = "GreenTech_DB"
COLLECTION_NAME = "manuals_vectors"
INDEX_NAME = "vector_index"

# 2. CONFIGURAMOS LOS MODELOS DE INTELIGENCIA ARTIFICIAL.
# Usamos HugginFace para transformar el texto en vectores (numeros que la IA entiende)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Configuramos a LLAMA 3.3 de Groq. le pusimos temperatura 0.2 para que no invente y sea totalmente serio
llm = ChatGroq(
    temperature=0.2, # Un poco de fluidez, pero mantenido en lo técnico
    groq_api_key=os.getenv("GROQ_API_KEY"), 
    model_name="llama-3.3-70b-versatile"
)

# 3. CONEXIÓN AL CEREBRO DE DATOS en este caso elegimos (MongoDB Atlas)
# Aqui nos conectamos a la base de datos donde subimos los PDFs con inges.py
client = MongoClient(os.getenv("MONGODB_ATLAS_URI"))
collection = client[DB_NAME][COLLECTION_NAME]

# Este es el buscador que comapra la pregunta del usuario con los manuales guardados
vector_search = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX_NAME
)

# 4. DISEÑO  DE LA INTERFAZ CON STREAMLIT
# COnfiguramos la pestana del navegador y el titulo principal
st.set_page_config(page_title="Academia Green Tech", page_icon="☀️", layout="wide")
st.title("🌱 Green Tech Academy: Mentor de Inducción")
st.markdown("""
---
**Bienvenido al equipo.** Soy tu Mentor IA. Mi objetivo es que domines los estándares de la empresa 
basándome en nuestros manuales técnicos oficiales.
""")

# PANEL LATERAL: Creamos botones para que el usuario no tenga que escribir todo
with st.sidebar:
    st.header(" Módulos de Aprendizaje")
    st.info("Haz clic para repasar conceptos clave:")
    
    #Si presiona un boton, se anade la pregunta automaticamente al historial
    if st.button(" Fundamentos Fotovoltaicos"):
        st.session_state.messages.append({"role": "user", "content": "Explícame cómo funcionan nuestros paneles y qué es el efecto fotoeléctrico."})
        
    if st.button(" Protocolos de Seguridad"):
        st.session_state.messages.append({"role": "user", "content": "¿Cuáles son las reglas de oro de seguridad eléctrica en Green Tech?"})
        
    if st.button(" Sistemas de Almacenamiento"):
        st.session_state.messages.append({"role": "user", "content": "¿Cómo se gestionan las baterías y el ciclo de carga?"})

    # Boton para limpiar el chat y empezar de cero
    if st.button(" Reiniciar Tutoría"):
        st.session_state.messages = []
        st.rerun()

# SISTEMA DE MEMORIO: Mantiene los mensajes visibles en la pantalla
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. EL MOTOR RAG (Busqueda + Respuesta)
# Cuando el usuario escribe algo en el chat:
if prompt := st.chat_input("Pregúntame cualquier duda técnica sobre el manual..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # PASO A: Buscamos en los manuales de Mongo los 4 parrafos mas parecidos a la pregunta
    docs = vector_search.similarity_search(prompt, k=4)
    contexto = "\n\n".join([doc.page_content for doc in docs])

    with st.chat_message("assistant"):
        # PASO B: Creamos el "Systema Prompt" que define la personalidad del Mentor.
        mensajes = [
            {
                "role": "system", 
                "content": """Eres el Mentor Senior de Ingeniería en Green Tech. Tu misión es capacitar a los nuevos empleados.
                
                ESTILO DE MENTORÍA:
                1. Rigor Técnico: Usa términos como Irradiancia, MPPT, Inversores de Cadena, Estructura Coplanar, etc.
                2. Seguridad Primero: Si la pregunta implica riesgo eléctrico o de altura, DEBES iniciar con una advertencia de seguridad.
                3. Formato Educativo: Usa negritas para conceptos clave y listas para procesos.
                4. Basado en Datos: Responde ÚNICAMENTE con la información del manual técnico proporcionado.
                5. Sin Inventos: Si algo no está en el manual, di: 'Ese tema no está cubierto en la documentación de inducción actual, por favor consúltalo con un supervisor humano'."""
            },
            # PASO C: Le pasamos el contexto recuperado de los PDFs y la pregunta
            {
                "role": "user", 
                "content": f"MANUALES TÉCNICOS DE APOYO:\n{contexto}\n\nPREGUNTA DEL APRENDIZ: {prompt}"
            }
        ]

        # Le pidemos a GROQ que procese todo y nos de la respuesta final.
        response = llm.invoke(mensajes)
        respuesta_final = response.content
        
        st.markdown(respuesta_final)
        st.session_state.messages.append({"role": "assistant", "content": respuesta_final})