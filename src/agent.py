from dataclasses import dataclass

from langchain_groq import ChatGroq

from src.memory import LongTermMemoryStore
from src.planner import Intent, Plan, classify_intent
from src.prompts import build_rag_messages, build_simple_answer_messages
from src.tools import GreenTechTools, build_tools


@dataclass
class AgentResponse:
    answer: str
    plan: Plan
    context: str
    short_memory: str
    long_memory: str


class GreenTechAgent:
    def __init__(
        self,
        tools: GreenTechTools,
        llm: ChatGroq,
        memory_store: LongTermMemoryStore,
        system_prompt: str,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory_store = memory_store
        self.system_prompt = system_prompt
        self.tool_registry = {tool.name: tool for tool in build_tools(tools)}

    def run(self, question: str) -> AgentResponse:
        has_short_memory = bool(self.tools.memory)
        plan = classify_intent(question, has_memory=has_short_memory)

        self.tool_registry["save_memory_tool"].invoke({"role": "user", "content": question})
        short_memory = self.tool_registry["get_memory_tool"].invoke({})
        long_memory = self.memory_store.format_relevant_memories(question) if plan.use_memory else ""

        if plan.ask_clarification:
            answer = "Necesito un poco mas de informacion para responder bien. Puedes reformular la pregunta con mas detalle?"
            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            return AgentResponse(answer, plan, "", short_memory, long_memory)

        if plan.intent == Intent.CONSULTA_SIMPLE:
            answer = self._answer_simple(question, short_memory, long_memory)
            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            self.memory_store.save_interaction(question, answer, plan.intent.value)
            return AgentResponse(answer, plan, "", short_memory, long_memory)

        context = self.tool_registry["search_documents_tool"].invoke({"query": question}) if plan.use_documents else ""
        if not context.strip():
            answer = (
                "No encontre informacion suficiente en los manuales cargados para responder con rigor. "
                "Valida este tema con un supervisor humano o con documentacion tecnica oficial adicional."
            )
            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            return AgentResponse(answer, plan, context, short_memory, long_memory)

        if plan.generate_report:
            answer = self.tools.generate_report(question, context)
        else:
            answer = self.llm.invoke(self._build_messages(question, context, short_memory, long_memory, plan)).content

        self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
        self.memory_store.save_interaction(question, answer, plan.intent.value)
        return AgentResponse(answer, plan, context, short_memory, long_memory)

    def _answer_simple(self, question: str, short_memory: str, long_memory: str) -> str:
        messages = build_simple_answer_messages(question, short_memory, long_memory, self.system_prompt)
        return self.llm.invoke(messages).content

    def _build_messages(
        self,
        question: str,
        context: str,
        short_memory: str,
        long_memory: str,
        plan: Plan,
    ) -> list[dict[str, str]]:
        return build_rag_messages(
            question=question,
            context=context,
            short_memory=short_memory,
            long_memory=long_memory,
            intent=plan.intent.value,
            reason=plan.reason,
            system_prompt=self.system_prompt,
        )
