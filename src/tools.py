from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_mongodb import MongoDBAtlasVectorSearch


class GreenTechTools:
    def __init__(
        self,
        vector_search: MongoDBAtlasVectorSearch,
        llm: ChatGroq,
        memory: list[dict[str, str]],
        system_prompt: str,
    ) -> None:
        self.vector_search = vector_search
        self.llm = llm
        self.memory = memory
        self.system_prompt = system_prompt

    def search_documents(self, query: str) -> str:
        docs = self.vector_search.similarity_search(query, k=4)
        return "\n\n".join(doc.page_content for doc in docs)

    def get_memory(self) -> str:
        if not self.memory:
            return "No hay mensajes previos en esta sesion."

        return "\n".join(
            f"{message['role']}: {message['content']}"
            for message in self.memory[-6:]
        )

    def save_memory(self, role: str, content: str) -> str:
        self.memory.append({"role": role, "content": content})
        return "Memoria guardada correctamente."

    def generate_report(self, topic: str, context: str | None = None) -> str:
        report_context = context or self.search_documents(topic)
        report_prompt = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Genera un reporte ejecutivo breve y tecnico para GreenTech.\n\n"
                    "Usa esta estructura:\n"
                    "1. Resumen ejecutivo\n"
                    "2. Hallazgos tecnicos\n"
                    "3. Riesgos o consideraciones de seguridad\n"
                    "4. Recomendaciones\n\n"
                    f"CONTEXTO DOCUMENTAL:\n{report_context}\n\n"
                    f"SOLICITUD:\n{topic}"
                ),
            },
        ]
        return self.llm.invoke(report_prompt).content


def build_tools(greentech_tools: GreenTechTools):
    @tool
    def search_documents_tool(query: str) -> str:
        """Busca informacion tecnica en los documentos cargados en MongoDB Atlas."""
        return greentech_tools.search_documents(query)

    @tool
    def get_memory_tool() -> str:
        """Recupera la memoria reciente de la conversacion actual."""
        return greentech_tools.get_memory()

    @tool
    def save_memory_tool(role: str, content: str) -> str:
        """Guarda un mensaje importante en la memoria corta de la sesion."""
        return greentech_tools.save_memory(role, content)

    @tool
    def generate_report_tool(topic: str) -> str:
        """Genera un reporte ejecutivo usando el contexto tecnico recuperado."""
        return greentech_tools.generate_report(topic)

    return [
        search_documents_tool,
        get_memory_tool,
        save_memory_tool,
        generate_report_tool,
    ]


def is_report_request(question: str) -> bool:
    report_keywords = ["reporte", "informe", "resumen ejecutivo", "documento ejecutivo"]
    normalized_question = question.lower()
    return any(keyword in normalized_question for keyword in report_keywords)
