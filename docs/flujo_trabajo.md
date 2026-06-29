# Flujo de trabajo del agente
Este flujo muestra que ocurre desde que el usuario escrbire una pregunta hasta que recibe respuesta.

```mermaid
flowchart TD
    A[Usuario escribe pregunta] --> B[Streamlit recibe input]
    B --> C[GreenTechAgent recibe pregunta]
    C --> D[Planner clasifica intencion]

    D --> E{Tipo de intencion}

    E -->|consulta_simple| F[Responder directo con memoria]
    E -->|solicitud_reporte| H[Buscar documentos y generar reporte]
    E -->|consulta_tecnica| G[Buscar documentos en MongoDB]
    E -->|continuidad_contexto| I[Usar memoria corta y larga]
    E -->|informacion_insuficiente| J[Pedir mas datos]

    G --> K[Armar prompt RAG]
    H --> K
    I --> K
    F --> L[Groq genera respuesta]
    K --> L
    J --> M[Respuesta pide aclaracion]
    L --> N[Guardar respuesta en memoria]
    M --> N
    N --> O[Mostrar respuesta en Streamlit]
```

## Explicacion

1. El suaurio escribre una pregunta.
2. Streamlit envia la pregunta al agente.
3. El agente usa el planner para detectar la intencion.
4. SEgun l aintencion, decide si usa documentos, memoria o reporte.
5. Si usa cdocumentos, busca contexto en MongoDB Atlas.
6. El Agente arma el rpompt.
7. Groq genera la respuesta.
8. La respuesta se guarda en memoria y se muestra al usuario