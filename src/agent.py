import time
from dataclasses import dataclass
from typing import Any

from langchain_groq import ChatGroq

from src.memory import LongTermMemoryStore
from src.planner import Intent, Plan, classify_intent
from src.prompts import build_rag_messages, build_simple_answer_messages
from src.tools import GreenTechTools, build_tools
from src.security import apply_safety_guardrails, needs_safety_warning, SAFETY_WARNING
from src.observability import ObservabilityLogger


@dataclass
class AgentResponse:
    answer: str
    plan: Plan
    context: str
    short_memory: str
    long_memory: str
    security_alert: bool = False


def get_token_usage(response: Any, prompt_text: str = "") -> dict[str, int]:
    """Extrae el uso de tokens de la respuesta de LangChain / Groq o realiza una estimación."""
    if hasattr(response, "response_metadata") and response.response_metadata:
        usage = response.response_metadata.get("token_usage")
        if usage:
            return {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
    
    # Estimación de fallback (1 token aprox. 4 caracteres)
    prompt_len = len(prompt_text)
    completion_len = len(response.content) if hasattr(response, "content") else len(str(response))
    
    input_tokens = max(10, prompt_len // 4)
    output_tokens = max(10, completion_len // 4)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


class GreenTechAgent:
    def __init__(
        self,
        tools: GreenTechTools,
        llm: ChatGroq,
        memory_store: LongTermMemoryStore,
        system_prompt: str,
        observability_logger: ObservabilityLogger | None = None,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory_store = memory_store
        self.system_prompt = system_prompt
        self.tool_registry = {tool.name: tool for tool in build_tools(tools)}
        self.observability_logger = observability_logger or ObservabilityLogger()

    def run(self, question: str) -> AgentResponse:
        total_start = time.perf_counter()
        latencies = {"planner": 0.0, "retrieval": 0.0, "generation": 0.0, "security": 0.0}
        
        # 1. Fase de Seguridad (Guardrails de Entrada)
        sec_start = time.perf_counter()
        sanitized_question, es_segura, mensaje_error = apply_safety_guardrails(question)
        latencies["security"] = time.perf_counter() - sec_start

        if not es_segura:
            latencies["total"] = time.perf_counter() - total_start
            # Registrar bloqueo de seguridad
            self.observability_logger.log_execution(
                question=question,
                answer=mensaje_error,
                intent="security_blocked",
                latencies=latencies,
                tokens={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                status="security_block",
                error_message="Consulta bloqueada por políticas de seguridad (Prompt Injection).",
                relevance_score=0.0,
                security_alert=True,
            )
            return AgentResponse(
                answer=mensaje_error,
                plan=Plan(
                    intent=Intent.INFORMACION_INSUFICIENTE,
                    reason="La consulta viola las directrices de seguridad.",
                    use_documents=False,
                    use_memory=False,
                    generate_report=False,
                    ask_clarification=False,
                ),
                context="",
                short_memory="",
                long_memory="",
                security_alert=True,
            )

        # 2. Fase de Planificación (Intent Classification)
        plan_start = time.perf_counter()
        has_short_memory = bool(self.tools.memory)
        plan = classify_intent(sanitized_question, has_memory=has_short_memory)
        latencies["planner"] = time.perf_counter() - plan_start

        # Guardar en memoria corta y larga
        self.tool_registry["save_memory_tool"].invoke({"role": "user", "content": sanitized_question})
        short_memory = self.tool_registry["get_memory_tool"].invoke({})
        long_memory = self.memory_store.format_relevant_memories(sanitized_question) if plan.use_memory else ""

        if plan.ask_clarification:
            answer = "Necesito un poco mas de informacion para responder bien. Puedes reformular la pregunta con mas detalle?"
            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            latencies["total"] = time.perf_counter() - total_start
            
            self.observability_logger.log_execution(
                question=sanitized_question,
                answer=answer,
                intent=plan.intent.value,
                latencies=latencies,
                tokens={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                status="success",
                relevance_score=0.0,
            )
            return AgentResponse(answer, plan, "", short_memory, long_memory)

        if plan.intent == Intent.CONSULTA_SIMPLE:
            gen_start = time.perf_counter()
            messages = build_simple_answer_messages(sanitized_question, short_memory, long_memory, self.system_prompt)
            prompt_str = str(messages)
            
            response = self.llm.invoke(messages)
            answer = response.content
            tokens = get_token_usage(response, prompt_str)
            latencies["generation"] = time.perf_counter() - gen_start
            latencies["total"] = time.perf_counter() - total_start

            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            self.memory_store.save_interaction(sanitized_question, answer, plan.intent.value)

            self.observability_logger.log_execution(
                question=sanitized_question,
                answer=answer,
                intent=plan.intent.value,
                latencies=latencies,
                tokens=tokens,
                status="success",
                relevance_score=0.0,
            )
            return AgentResponse(answer, plan, "", short_memory, long_memory)

        # 3. Fase de Recuperación (Retrieval)
        ret_start = time.perf_counter()
        context = self.tool_registry["search_documents_tool"].invoke({"query": sanitized_question}) if plan.use_documents else ""
        latencies["retrieval"] = time.perf_counter() - ret_start

        # Calcular relevancia de la búsqueda semántica
        relevance_score = self.observability_logger.calculate_semantic_relevance(sanitized_question, context)

        if not context.strip():
            answer = (
                "No encontre informacion suficiente en los manuales cargados para responder con rigor. "
                "Valida este tema con un supervisor humano o con documentacion tecnica oficial adicional."
            )
            self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
            latencies["total"] = time.perf_counter() - total_start

            self.observability_logger.log_execution(
                question=sanitized_question,
                answer=answer,
                intent=plan.intent.value,
                latencies=latencies,
                tokens={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                status="warning_empty_retrieval",
                relevance_score=0.0,
            )
            return AgentResponse(answer, plan, context, short_memory, long_memory)

        # 4. Fase de Generación (LLM)
        gen_start = time.perf_counter()
        
        # Resetear métricas previas en la herramienta
        self.tools.last_token_usage = None
        
        if plan.generate_report:
            answer = self.tools.generate_report(sanitized_question, context)
            tokens = getattr(self.tools, "last_token_usage", None) or get_token_usage(answer, sanitized_question + context)
        else:
            messages = self._build_messages(sanitized_question, context, short_memory, long_memory, plan)
            prompt_str = str(messages)
            response = self.llm.invoke(messages)
            answer = response.content
            tokens = get_token_usage(response, prompt_str)

        # Inyectar advertencia de seguridad física responsable si aplica
        physical_warning_triggered = needs_safety_warning(sanitized_question)
        if physical_warning_triggered:
            answer = SAFETY_WARNING + answer

        latencies["generation"] = time.perf_counter() - gen_start
        latencies["total"] = time.perf_counter() - total_start

        self.tool_registry["save_memory_tool"].invoke({"role": "assistant", "content": answer})
        self.memory_store.save_interaction(sanitized_question, answer, plan.intent.value)

        # Guardar en logs
        self.observability_logger.log_execution(
            question=sanitized_question,
            answer=answer,
            intent=plan.intent.value,
            latencies=latencies,
            tokens=tokens,
            status="success",
            relevance_score=relevance_score,
            security_alert=physical_warning_triggered,
        )

        return AgentResponse(answer, plan, context, short_memory, long_memory, security_alert=physical_warning_triggered)

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
