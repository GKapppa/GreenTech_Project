# Diagrma de orquestacion
Este diagrama muestra como se comunican los componentes del Mentor IA GreenTech.

```mermaid
flowchart TD
U[Usuario] --> UI[Streamlit / ingest.py]
UI --> A[GreenTechAgent / src/agent.py]

A --> P[Planner / src/planner.py]
A --> T[Tools / src/tools.py]
A --> M[Memoria larga JSON / src/memory.py]
A --> PR[Prompts / src/prompts.py]

T --> VS[Vector Store / src/vectorstore.py]
VS --> DB[(MongoDB Atlas)]
DB --> PDF[PDFs vectorizados]

A --> LLM[Groq Llama 3.3]
LLM --> A
A --> UI
UI --> U
```

## Explicacion breve
1. El usuario escribe en Streamlit.
2. Streamlit envia la pregunta al agente.
3. El agente pide un plan al planner.
4. Si necesita documentos, usa tools y vectorstore.
5. MongoDB deveulve fragmnentos de los pdf.
6. El agente arma el prompt.
7. Groq genera la respuesta.
8. La respuesta vuelve al usuairo.