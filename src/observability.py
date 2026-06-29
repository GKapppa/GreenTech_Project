import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import psutil
from langchain_huggingface import HuggingFaceEmbeddings

COST_PER_MILLION_INPUT = 0.59
COST_PER_MILLION_OUTPUT = 0.79

ERROR_RATE_THRESHOLD = 0.1
LATENCY_P95_THRESHOLD_SECONDS = 3.5


def compute_cosine_similarity(v1: list[float] | np.ndarray, v2: list[float] | np.ndarray) -> float:
    """Calcula la similitud de coseno entre dos vectores."""
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    dot_product = np.dot(vec1, vec2)
    norm_v1 = np.linalg.norm(vec1)
    norm_v2 = np.linalg.norm(vec2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))


def get_system_metrics() -> dict[str, float]:
    """Obtiene uso de CPU y memoria del proceso actual."""
    process = psutil.Process(os.getpid())
    return {
        "cpu_percent": round(process.cpu_percent(interval=0.05), 2),
        "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
        "memory_percent": round(process.memory_percent(), 2),
        "num_threads": process.num_threads(),
    }


class ObservabilityLogger:
    def __init__(
        self,
        log_path: str = "data/logs/observability_logs.jsonl",
        embedding_model: HuggingFaceEmbeddings | None = None,
    ) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._embeddings = embedding_model

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            from src.vectorstore import get_embeddings
            self._embeddings = get_embeddings()
        return self._embeddings

    def calculate_semantic_relevance(self, query: str, context: str) -> float:
        """Calcula la similitud semántica entre la pregunta y el contexto recuperado."""
        if not context or not context.strip():
            return 0.0
        try:
            embeddings = self.get_embeddings()
            q_emb = embeddings.embed_query(query)
            c_emb = embeddings.embed_query(context)
            return compute_cosine_similarity(q_emb, c_emb)
        except Exception:
            return 0.0

    def calculate_answer_quality(
        self,
        answer: str,
        question: str = "",
    ) -> dict[str, Any]:
        """Calcula métricas de calidad de la respuesta generada."""
        if not answer or not answer.strip():
            return {
                "quality_score": 0.0,
                "completeness": 0.0,
                "has_answer": False,
                "answer_length": 0,
            }

        answer_lower = answer.lower()
        no_info_indicators = [
            "no encontré",
            "no tengo información",
            "no puedo responder",
            "no está en los documentos",
            "insuficiente",
            "no puedo ayudarte con eso",
        ]
        has_content = not any(ind in answer_lower for ind in no_info_indicators)

        completeness = min(1.0, len(answer) / 200)

        suspicious_patterns = [
            "i'm sorry",
            "lo siento",
            "as an ai",
            "i cannot",
            "unable to",
        ]
        is_uncertain = any(pattern in answer_lower for pattern in suspicious_patterns)

        quality_score = 0.0
        if has_content:
            quality_score = 0.7 + (0.3 * completeness)
        if is_uncertain:
            quality_score *= 0.5

        return {
            "quality_score": round(quality_score, 3),
            "completeness": round(completeness, 3),
            "has_answer": has_content,
            "answer_length": len(answer),
            "is_uncertain": is_uncertain,
        }

    def log_execution(
        self,
        question: str,
        answer: str,
        intent: str,
        latencies: dict[str, float],
        tokens: dict[str, int] | None = None,
        status: str = "success",
        error_message: str | None = None,
        relevance_score: float | None = None,
        security_alert: bool = False,
    ) -> dict[str, Any]:
        """Registra una ejecución completa del agente en un archivo JSON Lines."""
        if tokens is None:
            tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        input_cost = (tokens.get("input_tokens", 0) / 1_000_000) * COST_PER_MILLION_INPUT
        output_cost = (tokens.get("output_tokens", 0) / 1_000_000) * COST_PER_MILLION_OUTPUT
        estimated_cost = input_cost + output_cost

        quality_metrics = self.calculate_answer_quality(answer, question)
        system_metrics = get_system_metrics()

        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "answer_summary": answer[:200] if answer else "",
            "intent": intent,
            "latencies": {
                "planner": latencies.get("planner", 0.0),
                "retrieval": latencies.get("retrieval", 0.0),
                "generation": latencies.get("generation", 0.0),
                "security": latencies.get("security", 0.0),
                "total": latencies.get("total", 0.0),
            },
            "tokens": {
                "input_tokens": tokens.get("input_tokens", 0),
                "output_tokens": tokens.get("output_tokens", 0),
                "total_tokens": tokens.get("total_tokens", 0),
            },
            "estimated_cost_usd": round(estimated_cost, 6),
            "status": status,
            "error_message": error_message,
            "relevance_score": relevance_score if relevance_score is not None else 0.0,
            "security_alert": security_alert,
            "quality_score": quality_metrics["quality_score"],
            "completeness": quality_metrics["completeness"],
            "answer_length": quality_metrics["answer_length"],
            "system_metrics": system_metrics,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_record, ensure_ascii=False) + "\n")

        return log_record

    def load_logs(self) -> list[dict[str, Any]]:
        """Carga y devuelve todos los registros de observabilidad."""
        if not self.log_path.exists():
            return []

        logs = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        return logs

    def calculate_consistency(
        self,
        query_normalized: str,
        window_size: int = 10,
    ) -> dict[str, Any]:
        """Mide consistencia ante consultas similares o idénticas."""
        logs = self.load_logs()
        if len(logs) < 2:
            return {"consistent": 1.0, "variance_latency": 0.0, "sample_count": 0}

        similar_logs = []
        for log in logs[-50:]:
            q = log.get("question", "").lower().strip()
            if query_normalized.lower().strip() in q or q in query_normalized.lower().strip():
                similar_logs.append(log)

        if len(similar_logs) < 2:
            return {"consistent": 1.0, "variance_latency": 0.0, "sample_count": len(similar_logs)}

        answers = [log.get("answer_summary", "") for log in similar_logs]
        latencies = [log.get("latencies", {}).get("total", 0) for log in similar_logs]

        latency_variance = float(np.var(latencies)) if latencies else 0.0

        embeddings = self.get_embeddings()
        if len(answers) >= 2 and answers[0]:
            try:
                answer_embs = embeddings.embed_documents([a for a in answers if a])
                if len(answer_embs) >= 2:
                    similarities = []
                    for i in range(len(answer_embs)):
                        for j in range(i + 1, len(answer_embs)):
                            sim = compute_cosine_similarity(answer_embs[i], answer_embs[j])
                            similarities.append(sim)
                    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
                else:
                    avg_similarity = 1.0
            except Exception:
                avg_similarity = 1.0
        else:
            avg_similarity = 1.0

        return {
            "consistent": round(avg_similarity, 3),
            "variance_latency": round(latency_variance, 4),
            "sample_count": len(similar_logs),
        }


class AnomalyDetector:
    def __init__(self, logs: list[dict[str, Any]] | None = None) -> None:
        self.logs = logs or []
        self._df = None

    @property
    def df(self):
        if self._df is None and self.logs:
            try:
                import pandas as pd
                self._df = pd.DataFrame(self.logs)
                if "latencies" in self._df.columns:
                    self._df["latency_total"] = self._df["latencies"].apply(
                        lambda l: l.get("total", 0) if isinstance(l, dict) else 0
                    )
                if "tokens" in self._df.columns:
                    self._df["total_tokens"] = self._df["tokens"].apply(
                        lambda t: t.get("total_tokens", 0) if isinstance(t, dict) else 0
                    )
            except Exception:
                self._df = None
        return self._df

    def detect_latency_outliers(
        self,
        threshold_percentile: float = 95,
    ) -> list[dict[str, Any]]:
        """Detecta latencias anómalas usando el método del percentil 95."""
        if self.df is None or "latency_total" not in self.df.columns:
            return []

        p95 = self.df["latency_total"].quantile(threshold_percentile / 100)
        outliers = self.df[self.df["latency_total"] > p95]

        return outliers[["timestamp", "question", "latency_total", "intent", "status"]].to_dict("records")

    def detect_error_bursts(self, window_size: int = 5) -> list[dict[str, Any]]:
        """Detecta ráfagas de errores consecutivos."""
        if self.df is None or "status" not in self.df.columns:
            return []

        statuses = self.df["status"].tolist()
        bursts = []

        for i in range(len(statuses) - window_size + 1):
            window = statuses[i : i + window_size]
            error_count = sum(
                1 for s in window if "error" in str(s).lower() or "block" in str(s).lower()
            )
            if error_count >= window_size - 1:
                bursts.append(
                    {
                        "start_index": i,
                        "end_index": i + window_size - 1,
                        "error_count": error_count,
                        "window_start": self.logs[i].get("timestamp", ""),
                        "window_end": self.logs[i + window_size - 1].get("timestamp", ""),
                    }
                )

        return bursts

    def detect_error_patterns(self) -> dict[str, int]:
        """Identifica patrones de errores agrupados por intención."""
        if self.df is None:
            return {}

        errors = self.df[
            self.df["status"].str.contains("error|block", case=False, na=False)
        ]
        return errors["intent"].value_counts().to_dict() if not errors.empty else {}

    def calculate_error_rate(self, window_size: int = 10) -> list[dict[str, Any]]:
        """Calcula tasa de errores en ventanas móviles."""
        if self.df is None or "status" not in self.df.columns:
            return []

        statuses = self.df["status"].tolist()
        rates = []
        for i in range(len(statuses) - window_size + 1):
            window = statuses[i : i + window_size]
            total = len(window)
            errors = sum(
                1 for s in window if "error" in str(s).lower() or "block" in str(s).lower()
            )
            timestamp = self.logs[i].get("timestamp", "") if i < len(self.logs) else ""
            rates.append(
                {
                    "window": i + 1,
                    "timestamp": timestamp,
                    "error_rate": round(errors / total, 3) if total > 0 else 0,
                    "errors": errors,
                    "total": total,
                }
            )
        return rates

    def calculate_percentiles(self) -> dict[str, float]:
        """Calcula percentiles de latencia (P50, P95, P99)."""
        if self.df is None or "latency_total" not in self.df.columns:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        return {
            "p50": round(self.df["latency_total"].quantile(0.50), 3),
            "p95": round(self.df["latency_total"].quantile(0.95), 3),
            "p99": round(self.df["latency_total"].quantile(0.99), 3),
        }

    def calculate_token_stats(self) -> dict[str, Any]:
        """Calcula estadísticas de consumo de tokens."""
        if self.df is None or "total_tokens" not in self.df.columns:
            return {}

        return {
            "avg_input_tokens": round(self.df["tokens"].apply(
                lambda t: t.get("input_tokens", 0) if isinstance(t, dict) else 0
            ).mean(), 1) if "tokens" in self.df.columns else 0,
            "avg_output_tokens": round(self.df["tokens"].apply(
                lambda t: t.get("output_tokens", 0) if isinstance(t, dict) else 0
            ).mean(), 1) if "tokens" in self.df.columns else 0,
            "avg_total_tokens": round(self.df["total_tokens"].mean(), 1),
            "max_tokens": int(self.df["total_tokens"].max()),
            "total_tokens_processed": int(self.df["total_tokens"].sum()),
        }

    def get_recommendations(self) -> list[str]:
        """Genera recomendaciones automáticas basadas en patrones detectados."""
        recommendations = []

        if self.df is None:
            return recommendations

        error_df = self.df[
            self.df["status"].str.contains("error", case=False, na=False)
        ]
        if not error_df.empty:
            error_rate = len(error_df) / len(self.df)
            if error_rate > ERROR_RATE_THRESHOLD:
                recommendations.append(
                    f"Alerta: Tasa de error elevada ({error_rate*100:.1f}%). "
                    "Revisar conectividad a MongoDB Atlas y límites de la API Groq."
                )

        if "latency_total" in self.df.columns:
            avg_latency = self.df["latency_total"].mean()
            p95_latency = self.df["latency_total"].quantile(0.95)
            if avg_latency > 2.5:
                recommendations.append(
                    f"Latencia promedio alta ({avg_latency:.2f}s). "
                    "Considerar implementar caching semántico o modelo más rápido para consultas simples."
                )
            if p95_latency > LATENCY_P95_THRESHOLD_SECONDS:
                recommendations.append(
                    f"P95 de latencia elevado ({p95_latency:.2f}s). "
                    "La experiencia del 5% de usuarios con peores respuestas puede verse afectada."
                )

        security_blocks = self.df[self.df["status"] == "security_block"]
        if not security_blocks.empty:
            recommendations.append(
                f"{len(security_blocks)} intento(s) de acceso no autorizado bloqueado(s). "
                "Sistema de guardrails de seguridad operativo."
            )

        if "quality_score" in self.df.columns:
            low_quality = self.df[self.df["quality_score"] < 0.5]
            if not low_quality.empty:
                low_quality_rate = len(low_quality) / len(self.df)
                recommendations.append(
                    f"{(low_quality_rate*100):.1f}% de respuestas con calidad baja. "
                    "Revisar relevancia de documentos recuperados o ajustar prompts."
                )

        success_df = self.df[self.df["status"] == "success"]
        if not success_df.empty and "relevance_score" in success_df.columns:
            avg_relevance = success_df["relevance_score"].mean()
            if avg_relevance < 0.6:
                recommendations.append(
                    f"Relevancia RAG promedio baja ({avg_relevance:.2f}). "
                    "Evaluar calidad de embeddings o implementar reranking."
                )

        return recommendations

    def generate_summary(self) -> dict[str, Any]:
        """Genera un resumen completo del análisis de observabilidad."""
        if not self.logs:
            return {
                "total_queries": 0,
                "error_rate": 0.0,
                "avg_latency": 0.0,
                "recommendations": [],
            }

        total = len(self.logs)
        errors = sum(
            1 for log in self.logs
            if "error" in str(log.get("status", "")).lower()
            or "block" in str(log.get("status", "")).lower()
        )

        latencies = [
            log.get("latencies", {}).get("total", 0)
            for log in self.logs
            if isinstance(log.get("latencies"), dict)
        ]

        return {
            "total_queries": total,
            "error_count": errors,
            "error_rate": round(errors / total, 3) if total > 0 else 0.0,
            "success_count": total - errors,
            "success_rate": round((total - errors) / total, 3) if total > 0 else 0.0,
            "avg_latency": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "percentiles": self.calculate_percentiles(),
            "token_stats": self.calculate_token_stats(),
            "error_patterns": self.detect_error_patterns(),
            "latency_outliers": len(self.detect_latency_outliers()),
            "recommendations": self.get_recommendations(),
        }
