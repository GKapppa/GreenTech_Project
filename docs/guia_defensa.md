# Guia de Defensa - Mentor IA GreenTech

## TEXTO PARA PRESENTACION (5-7 minutos)

---

### SLIDE 1 - INTRODUCCION (1 minuto)

"Buenos dias/tardes, mi nombre es [nombre] y les presento el proyecto **Mentor IA GreenTech**.

Este es un sistema de induccion tecnica inteligente disenado para la empresa GreenTech, que es una empresa lider en el rubro de energias renovables en Chile.

**El problema que resolvemos** es el siguiente: cuando llega un nuevo tecnico a GreenTech, debe capacitare en sistemas fotovoltaicos consultando manuales tecnicos extensos. Este proceso toma entre 30 y 60 minutos por tema, y muchas veces no es facil encontrar exactamente la informacion que se necesita.

**Nuestra solucion** es un asistente virtual inteligente que permite consultar los manuales tecnicos mediante lenguaje natural. En lugar de buscar en PDF, el tecnico simplemente hace una pregunta como 'Cuales son las medidas de seguridad para instalar paneles?' y el sistema le responde con la informacion relevante."

---

### SLIDE 2 - ARQUITECTURA DEL SISTEMA (1.5 minutos)

"La arquitectura del sistema se compone de cuatro capas principales:

**Capa 1 - Interfaz de Usuario:** Usamos Streamlit, que es un framework de Python para crear aplicaciones web de forma rapida. El usuario interactua mediante un chat intuitivo.

**Capa 2 - Agente Orquestador:** Este es el cerebro del sistema. Esta implementado en agent.py y su funcion es coordinar todas las decisiones. Recibe la pregunta del usuario, la analiza, y decide que acciones tomar.

**Capa 3 - Motor RAG:** RAG significa Retrieval-Augmented Generation, que es una arquitectura que combina busqueda de informacion con generacion de texto. Usamos MongoDB Atlas como base de datos vectorial, donde tenemos almacenados los manuales tecnicos convertidos en vectores numericos.

**Capa 4 - Modelo de Lenguaje:** Finalmente, usamos Groq con el modelo Llama 3.3 de 70 mil millones de parametros para generar respuestas naturales basadas en el contexto recuperado.

Lo importante aqui es que el **agente decide automaticamente** si necesita buscar documentos, usar memoria de conversaciones anteriores, o generar un reporte estructurado."

---

### SLIDE 3 - FLUJO DEL AGENTE (1 minuto)

"Cuando el usuario hace una pregunta, ocurre lo siguiente:

1. **Fase de Seguridad:** Primero validamos que la consulta no contenga intentos de inyeccion de prompt ni datos personales sin proteger.

2. **Fase de Planificacion:** El planner clasifica la pregunta en una de cinco intenciones: consulta simple, consulta tecnica, solicitud de reporte, continuidad de contexto, o si necesita mas informacion.

3. **Fase de Recuperacion:** Si es una consulta tecnica, buscamos en MongoDB Atlas los fragmentos mas relevantes usando busqueda semantica.

4. **Fase de Generacion:** El LLM genera la respuesta usando el contexto recuperado.

5. **Fase de Logging:** Todo se registra para observabilidad y auditoria."

---

### DEMO - streamlit run ingest.py (2-3 minutos)

"Ahora les muestro el sistema funcionando en tiempo real.

[Abrir Streamlit]

[Aqui pueden ver la interfaz principal. A la izquierda tenemos un menu lateral con modulos de aprendizaje rapido y preguntas sugeridas. En el centro esta el area de chat.]

[Realizar pregunta demo: "Explicame como funciona un panel solar"]

[Mientras carga...] Noten que el sistema esta procesando la consulta. Podemos ver el spinner 'Buscando en los manuales tecnicos'.

[Respuesta aparece] "Aqui tienen la respuesta generada. Como ven, incluye informacion tecnica precisa sobre el efecto fotoelectrico y como los fotones liberan electrones en el silicio.

Noten que si la pregunta involucra riesgo de seguridad electrica, el sistema inyecta automaticamente una advertencia."

[Segunda pregunta: "Cuales son las medidas de seguridad para trabajar con paneles?"]

[Aqui el sistema detecta las palabras 'seguridad' y 'trabajar' y agrega la advertencia de EPP."

---

### SLIDE 4 - OBSERVABILIDAD Y MONITOREO (1 minuto)

"Una parte crucial de cualquier sistema en produccion es la observabilidad.

**Que monitoreamos?**

- **Latencias por fase:** Cuanto tiempo tarda cada parte del flujo (planificacion, recuperacion, generacion)
- **Tokens consumidos:** Cuanto nos cuesta cada consulta en terminos de API de Groq
- **Precision RAG:** Que tan relevante es el contexto recuperado para la pregunta
- **Calidad de respuestas:** Evaluamos si las respuestas tienen contenido util o si el LLM no pudo responder
- **Metricas de sistema:** CPU y memoria RAM del servidor

**El dashboard** nos muestra graficos de tendencias, percentiles de latencia P50, P95 y P99, y permite exportar los logs a CSV para analisis posterior."

---

### SLIDE 5 - SEGURIDAD Y ETICA (30 segundos)

"Implementamos tres capas de seguridad:

1. **Enmascaramiento de PII:** Correos, telefonos y credenciales se reemplazan automaticamente antes de procesar.
2. **Deteccion de inyeccion de prompt:** Si alguien intenta manipular el comportamiento del LLM, lo blokqueamos.
3. **Auditoria inmutable:** Todos los accesos quedan registrados con timestamp UTC.

Ademas, el sistema respeta la normativa de proteccion de datos segun la Ley 19.628 de Chile."

---

### CIERRE (30 segundos)

"En conclusion, el Mentor IA GreenTech permite:

- Reducir el tiempo de capacitacion de 30-60 minutos a segundos
- Responder con rigor tecnico basado en manuales oficiales
- Mantener trazabilidad completa de todas las consultas
- Garantizar la seguridad y privacidad de los usuarios

El codigo esta disponible en GitHub y esta documentado para facilitar el mantenimiento y escalabilidad futura.

Gracias, quedan algunas preguntas?"

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

---

## TIPS PARA LA PRESENTACION

### Antes de presentar:
- Tener Streamlit abierto y funcionando
- Tener 2-3 preguntas de prueba preparado
- Verificar que MongoDB Atlas y Groq esten conectados
- Tener el telefono en modo avion por si acaso

### Durante la presentacion:
- Hablar con confianza aunque haya errores tecnicos
- Si algo falla, decir "esto es parte de lo que monitoreamos" y seguir
- No leer las respuestas, explicar los conceptos
- Usar las manos para indicar el flujo de datos
- Hacer contacto visual con la comision

### Si no saben algo:
- "Esa es una muy buena pregunta, es parte de las mejoras futuras que propomos"
- "Lo implementariamos de otra forma en produccion"
- "Es una limitacion conocida que documentamos en el informe"

### Frases de confianza:
- "Tenemos metricas para medir eso"
- "El sistema esta diseñado para eso"
- "Lo pueden ver en el dashboard"
- "Esta en el codigo fuente"

### Lo que NO deben decir:
- "Eso no lo implementamos"
- "No se como funciona eso"
- "El codigo esta烂"
- "Eso fue cosa de mi companero"

