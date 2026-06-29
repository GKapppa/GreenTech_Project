# Mentor IA - GreenTech Project

Sistema de mentor de induccion tecnica para GreenTech. Permite realizar preguntas
sobre sistemas fotovoltaicos y recibir respuestas basadas en los manuales tecnicos
del proyecto mediante recuperacion semantica (RAG).

## Arquitectura del sistema

```
Usuario -> Streamlit (ingest.py) -> GreenTechAgent
                                      |
                                      +-> Planner (clasificacion de intencion)
                                      +-> Tools (busqueda, memoria, reportes)
                                      +-> ObservabilityLogger (telemetria)
                                      +-> SecurityGuardrails (PII, inyeccion)
                                      +-> SemanticCache (caching)
                                      |
                                      +-> MongoDB Atlas Vector Search
                                      +-> Groq Llama 3.3
```

## Estructura del proyecto

```
greentech/
├── ingest.py                  Aplicacion principal Streamlit con dashboard
├── src/
│   ├── agent.py               Agente principal con orchestracion
│   ├── planner.py             Clasificador de intenciones
│   ├── tools.py               Herramientas registradas con @tool
│   ├── memory.py              Memoria larga en JSON
│   ├── prompts.py             Plantillas de prompts
│   ├── vectorstore.py         Configuracion de MongoDB Atlas
│   ├── observability.py       Sistema de metricas y deteccion de anomalias
│   ├── security.py            Guardrails eticos y de privacidad
│   └── cache.py               Cache semantico para respuestas frecuentes
├── tests/                     Pruebas automatizadas
├── docs/                      Documentacion tecnica
├── data/
│   ├── logs/                  Logs de observabilidad y auditoria
│   └── memory/                Memoria larga persistente
└── requirements.txt           Dependencias del proyecto
```

## Funcionalidades implementadas

### RAG y recuperacion semantica

- Embeddings con `HuggingFaceEmbeddings` (modelo `all-MiniLM-L6-v2`)
- Busqueda vectorial en MongoDB Atlas
- Indice `vector_index` en coleccion `manuals_vectors`
- Fragmentacion automatica de documentos PDF

### Sistema de observabilidad

El modulo `observability.py` implementa:

- **Metric logging**: latencias por fase, tokens consumidos, costo USD estimado
- **Quality scoring**: evaluacion de calidad de respuestas generadas
- **System metrics**: uso de CPU, memoria RAM y threads del proceso
- **AnomalyDetector**: deteccion automatica de latencias anomalas (P95),
  rafagas de errores y patrones de falla por intencion
- **Percentiles P50/P95/P99**: analisis estadistico de latencias

### Dashboard de monitoreo

La pestana "Dashboard de Observabilidad" en Streamlit muestra:

- Tarjetas KPI: consultas totales, latencia promedio, tasa de exito,
  precision RAG, alertas de seguridad, costo acumulado
- Graficos de tendencia temporal para latencias y tokens
- Distribucion de intenciones clasificadas
- Analisis de anomalias con recomendaciones automaticas
- Percentiles de latencia y patrones de error
- Explorador de logs con filtros y exportacion a CSV

### Seguridad y compliance

El modulo `security.py` implementa:

- **Enmascaramiento de PII**: correos electronicos, telefonos, credenciales API
- **Deteccion de inyeccion de prompt**: palabras clave sospechosas
- **Advertencias de seguridad fisica**: para consultas sobre riesgo electrico o alturas
- **Auditoria de accesos**: logs inmutables con session ID y timestamp UTC
- **Consentimiento**: registro de aceptacion de politicas de uso
- **Politica de retencion**: maxima de 90 dias para logs de observabilidad

### Cache semantico

El modulo `cache.py` implementa:

- Almacenamiento de respuestas basadas en similitud TF-IDF
- Umbral de similitud configurable (default 0.92)
- Estadisticas de uso: hits, latencia ahorrada, tokens economizados
- Eviccion automatica de entradas mas antiguas (LRU)
- Persistencia en archivo JSON Lines

### Clasificador de intenciones

El `planner.py` clasifica cada consulta en:

- `consulta_simple`: respuesta directa con memoria
- `consulta_tecnica`: busqueda de documentos + RAG
- `solicitud_reporte`: generacion de reporte estructurado
- `continuidad_contexto`: incluye memoria corta y larga
- `informacion_insuficiente`: pide aclaracion al usuario

## Instalacion

```powershell
cd M:\GreenTech_Project
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Configuracion de variables de entorno

Crear archivo `.env` en la raiz:

```env
GROQ_API_KEY=tu_api_key_de_groq
MONGODB_ATLAS_URI=tu_uri_de_mongodb_atlas
```

## Carga de documentos

Antes de usar el chat, cargar los PDF en MongoDB Atlas:

```powershell
.\venv\Scripts\python.exe load_pdfs.py --reset
```

## Ejecucion

```powershell
streamlit run ingest.py
```

Abrir en el navegador: `http://localhost:8501`

## Ejecucion con Docker

```powershell
docker build -t greentech-mentor .
docker run --env-file .env -p 8501:8501 greentech-mentor
```

## Ejecucion de pruebas

```powershell
.\venv\Scripts\python.exe -m pytest tests/
```

## Ejemplos de consultas

```text
Explicame como funcionan los paneles solares y que es el efecto fotoelectrico.
```

```text
Cuales son las principales medidas de seguridad para instalar paneles fotovoltaicos?
```

```text
Genera un reporte ejecutivo sobre seguridad en instalaciones fotovoltaicas.
```

## Modulos de aprendizaje rapido

La barra lateral de Streamlit incluye botones para consultas guiadas sobre:

- Fundamentos Fotovoltaicos
- Protocolos de Seguridad
- Sistemas de Almacenamiento

## Limitaciones y trabajo futuro

- La memoria larga usa resumenes simples; no hace compresion avanzada de conversaciones
- Los PDF deben cargarse previamente con `load_pdfs.py`
- La deteccion de reportes es por palabras clave (`reporte`, `informe`, `resumen`)
- Se propone implementar busqueda hibrida (vectorial + BM25) con reranking
- Se propone migrar Planner y Guardrails a un modelo SLM local

## Historial de cambios

### Fase 3: Observabilidad y trazabilidad

- Sistema de metricas de rendimiento con AnomalyDetector
- Dashboard interactivo con analisis en tiempo real
- Cache semantico para reducir latencia y costo
- Guardrails de seguridad y auditoria de compliance
- Logging de calidad de respuestas

### Fase 2: Agente con planificacion

- Clasificador de intenciones
- Herramientas registradas con @tool de LangChain
- Memoria corta y larga
- Generacion de reportes estructurados

### Fase 1: MVP con RAG

- Busqueda vectorial en MongoDB Atlas
- Interface Streamlit
- Integracion con Groq LLM
