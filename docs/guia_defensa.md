# Guia de Defensa - Mentor IA GreenTech

## TEXTO PARA PRESENTACION (2-3 minutos)

---

**SLIDE 1 - INTRODUCCION:**

"Buenos dias, soy [nombre] y les presento el proyecto Mentor IA GreenTech, un sistema de induccion tecnica basado en agentes inteligentes para la empresa GreenTech del rubro energetico renovable.

El problema que resuelve es que los nuevos tecnicos necesitan consultar manuales tecnicos extensos sobre sistemas fotovoltaicos, lo cual toma tiempo y no siempre es facil encontrar la informacion correcta.

Nuestra solucion es un chat inteligente que responde preguntas tecnicas usando recuperacion semantica y un modelo de lenguaje."

---

**SLIDE 2 - ARQUITECTURA:**

"La arquitectura se compone de cuatro capas:

1. interfaz Streamlit donde el usuario hace preguntas
2. Un agente orchestrador que clasifica la intencion del usuario
3. Motor RAG con busqueda vectorial en MongoDB Atlas
4. Modelo LLM Groq Llama 3.3 para generar respuestas

El agente decide automaticamente si necesita buscar documentos, usar memoria o generar un reporte."

---

**DEMO - streamlit run ingest.py:**

"Aqui pueden ver la aplicacion funcionando. Voy a hacer una pregunta tecnica..."

**Pregunta demo:** "Explicame como funciona un panel solar"

"Como ven, el sistema identifica la intencion como consulta tecnica, busca en los manuales vectorizados, recupera el contexto relevante y genera una respuesta con rigor tecnico.

Noten que incluye advertencias de seguridad automaticamente cuando detecta riesgo electrico."

---

## PREGUNTAS DE LA COMISION - RESPUESTAS

### PREGUNTAS SOBRE RAG Y RECUPERACION

**P: "Como recupera informacion el agente desde los documentos?"**
R: "Usamos embeddings del modelo all-MiniLM-L6-v2 de HuggingFace. Cada fragmento de los PDFs se convierte en un vector de 384 dimensiones. Cuando el usuario pregunta, la pregunta tambien se Embedda y se busca en MongoDB Atlas usando busqueda de similitud coseno. Los fragmentos mas similares se recuperan como contexto para el LLM."

**P: "Que pasa si la busqueda no encuentra contexto relevante?"**
R: "El sistema tiene un umbral de relevancia. Si la similitud es muy baja, el agente responde con conocimiento propio del dominio fotovoltaico pero indicando transparencia. Esto se loggea como 'warning_empty_retrieval' en los logs de observabilidad."

**P: "Cuantos documentos tienen cargados?"**
R: "Tres manuales tecnicos principales: el manual general de GreenTech, la guia de instalacion de sistemas fotovoltaicos de 2013, y la guia de evaluacion de sistemas. Aproximadamente 92 fragmentos vectorizados en MongoDB Atlas."

---

### PREGUNTAS SOBRE EL AGENTE

**P: "Como decide el agente que tipo de respuesta dar?"**
R: "El planner.py clasifica la pregunta en cinco intenciones: consulta simple, consulta tecnica, solicitud de reporte, continuidad de contexto, o informacion insuficiente. Esto se hace con keywords y heuristicas. Por ejemplo, si la pregunta tiene palabras como 'fotovoltaico', 'inversor' o 'panel', se clasifica como tecnica."

**P: "Que es el planner exactamente?"**
R: "Es un clasificador de intenciones basado en reglas. Analiza la pregunta y decide si el agente debe: buscar documentos, usar memoria, generar un reporte, o pedir mas informacion. Esta decision se pasa al orquestador del agente."

**P: "Como maneja la memoria?"**
R: "Tenemos dos tipos: memoria corta que usa st.session_state y mantiene el historial mientras la app esta abierta, y memoria larga que guarda resumenes de conversaciones anteriores en un archivo JSON. Esto permite continuidad en conversaciones prolongadas."

---

### PREGUNTAS SOBRE OBSERVABILIDAD (LO MAS IMPORTANTE)

**P: "Que metricas estan monitoreando?"**
R: "Monitoreamos cuatro categorias:
1. Latencias por fase: planner, retrieval, generation, security
2. Tokens consumidos: input, output, total
3. Precision RAG: similitud coseno entre pregunta y contexto recuperado
4. Calidad de respuestas: evaluamos si la respuesta tiene contenido util

Tambien medimos CPU y memoria del proceso con psutil."

**P: "Como detectan anomalias?"**
R: "Implementamos un AnomalyDetector que usa el percentil 95. Si una latencia supera el P95, se marca como anomalia. Tambien detecta rafagas de errores consecutivos y calcula la tasa de error en ventanas moviles de 10 consultas. Todo esto genera recomendaciones automaticas."

**P: "Que informacion muestra el dashboard?"**
R: "El dashboard tiene tres pestanas: chat tutoral, panel de observabilidad con 6 KPIs principales, y auditoria de compliance. En el panel hay graficos de tendencia de latencias, distribucion de intenciones, consumo de tokens, percentiles P50/P95/P99, y un explorador de logs con filtros y exportacion a CSV."

**P: "Cuantas consultas han procesado?"**
R: "Tenemos aproximadamente 20 consultas en los logs de prueba. La tasa de exito promedio es del 70-80%. El costo acumulado en tokens es de aproximadamente 0.01 USD."

---

### PREGUNTAS SOBRE SEGURIDAD

**P: "Como protegen datos personales de los usuarios?"**
R: "Implementamos tres capas: primero, enmascaramiento de PII con regex para correos, telefonos y credenciales API. Segundo, deteccion de inyeccion de prompt con keywords sospechosas. Ter cero, auditamos todos los accesos con timestamp UTC y session ID en un log inmutable."

**P: "Que hacen para prevenir inyeccion de prompt?"**
R: "El security.py tiene una lista de keywords como 'ignore previous instructions', 'system prompt', 'jailbreak'. Si se detecta alguna, la consulta se bloquea inmediatamente sin consumir recursos del LLM. Esto se loggea como 'security_block'."

**P: "Hay alguna normativa de compliance?"**
R: "Si. Implementamos referencia a la Ley 19.628 de Chile de proteccion de datos personales, GDPR y NIST AI Risk Management Framework. Los logs se retienen maximo 90 dias. El consentimiento del usuario se registra automaticamente."

---

### PREGUNTAS SOBRE LIMITACIONES Y MEJORAS

**P: "Cuales son las limitaciones de tu solucion?"**
R: "1. La precision RAG depende de la calidad de los embeddings y la fragmentacion de documentos.
2. El agente usa clasificacion por reglas, no por ML.
3. No tenemos pruebas automatizadas de extremo a extremo.
4. La memoria larga es simple, no usa compresion avanzada."

**P: "Que pasaria si el LLM alucina una respuesta?"**
R: "El prompt esta disenado para responder solo con informacion de los manuales. Ademas, si el contexto recuperado tiene baja similitud, el sistema avisa que debe consultarse un supervisor. Finalmente, tenemos metricas de calidad que detectan respuestas sin contenido util."

**P: "Como escalarian este sistema?"**
R: "Propomos tres mejoras: primero, caching semantico con TF-IDF para consultas similares. Segundo, usar un modelo SLM mas pequeno para tareas auxiliares como el planner. Tercero, busqueda hibrida con BM25 y reranking para mejorar la precision de recuperacion."

---

### PREGUNTAS DE NEGOCIO

**P: "Cual es el caso de negocio?"
R: "Reducir el tiempo de induccion de nuevos tecnicos. Consultar manuales fisicos toma 30-60 minutos. Con el mentor IA, el mismo contenido se recupera en segundos. Ademas, reduce errores por interpretacion incorrecta de manuales."

**P: "Cuanto cuesta operar esto?"
R: "El costo principal es el LLM de Groq. Nuestra medicion muestra aproximadamente 0.0005 USD por consulta promedio. Para 1000 consultas diarias, serian 0.50 USD diarios, o 15 USD mensuales."

**P: "Quien es el usuario objetivo?"
R: "Tecnicos nuevos de GreenTech que necesitan capacitacion en sistemas fotovoltaicos. No requieren conocimientos previos de informatica, solo saber usar un chat."

---

## FRASES CLAVE PARA LA DEFENSA

- "El agente orchestrador decide el flujo de ejecucion"
- "La observabilidad nos permite detectar cuellos de botella"
- "El dashboard muestra metricas en tiempo real"
- "La seguridad tiene tres capas de proteccion"
- "El caching semantico reduce latencia y costo"
- "El planner clasifica en cinco intenciones posibles"
- "Los logs son inmutables y auditables"
- "El sistema alerta automaticamente sobre anomalias"
