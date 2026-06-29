import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticCache:
    def __init__(
        self,
        cache_path: str = "data/logs/semantic_cache.jsonl",
        similarity_threshold: float = 0.92,
        max_cache_size: int = 500,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self._vectorizer = TfidfVectorizer()
        self._cache: list[dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Carga el cache persistido desde el archivo JSON Lines."""
        if not self.cache_path.exists():
            return

        with open(self.cache_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        self._cache.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue

    def _save_cache_entry(self, entry: dict[str, Any]) -> None:
        """Guarda una entrada en el archivo de cache."""
        with open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get(self, query: str) -> tuple[str | None, dict[str, Any]]:
        """
        Busca en cache si existe una query semanticamente similar.

        Retorna:
            - respuesta en cache o None si no hay hit
            - metadatos del cache (hit_count, latency_saved, etc.)
        """
        metadata = {
            "cache_hit": False,
            "similarity": 0.0,
            "cached_answer": None,
            "query": query[:100],
        }

        if not self._cache:
            return None, metadata

        try:
            query_lower = query.lower()
            cached_queries = [item["query"].lower() for item in self._cache]
            cached_queries.append(query_lower)

            tfidf_matrix = self._vectorizer.fit_transform(cached_queries)
            similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]

            max_idx = int(np.argmax(similarities))
            max_similarity = float(similarities[max_idx])

            metadata["similarity"] = round(max_similarity, 4)

            if max_similarity >= self.similarity_threshold:
                cached_item = self._cache[max_idx]
                cached_item["hit_count"] = cached_item.get("hit_count", 0) + 1
                cached_item["last_accessed"] = datetime.now(timezone.utc).isoformat()

                metadata["cache_hit"] = True
                metadata["cached_answer"] = cached_item["answer"]
                metadata["cached_intent"] = cached_item.get("intent", "unknown")
                metadata["latency_saved"] = cached_item.get("original_latency", 0)
                metadata["tokens_saved"] = cached_item.get("original_tokens", 0)

                return cached_item["answer"], metadata

        except Exception:
            pass

        return None, metadata

    def add(
        self,
        query: str,
        answer: str,
        intent: str,
        latency: float,
        tokens_used: int,
        relevance_score: float = 0.0,
    ) -> None:
        """Agrega una query y respuesta al cache."""
        if not answer or len(answer.strip()) < 10:
            return

        if len(self._cache) >= self.max_cache_size:
            self._evict_oldest()

        entry = {
            "query": query,
            "answer": answer,
            "intent": intent,
            "original_latency": latency,
            "original_tokens": tokens_used,
            "relevance_score": relevance_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
        }

        self._cache.append(entry)
        self._save_cache_entry(entry)

    def _evict_oldest(self) -> None:
        """Elimina la entrada mas antigua del cache."""
        if not self._cache:
            return

        oldest_idx = 0
        oldest_time = self._cache[0].get("created_at", "")

        for i, item in enumerate(self._cache):
            item_time = item.get("created_at", "")
            if item_time < oldest_time:
                oldest_time = item_time
                oldest_idx = i

        self._cache.pop(oldest_idx)

        lines = []
        with open(self.cache_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if lines:
            lines.pop(oldest_idx)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

    def get_stats(self) -> dict[str, Any]:
        """Retorna estadisticas de uso del cache."""
        if not self._cache:
            return {
                "size": 0,
                "total_hits": 0,
                "avg_similarity_threshold": self.similarity_threshold,
                "estimated_latency_savings_ms": 0,
                "estimated_tokens_saved": 0,
                "hit_rate_last_10": 0.0,
            }

        total_hits = sum(item.get("hit_count", 0) for item in self._cache)

        latency_savings = sum(
            item.get("original_latency", 0) * item.get("hit_count", 0)
            for item in self._cache
        )
        tokens_saved = sum(
            item.get("original_tokens", 0) * item.get("hit_count", 0)
            for item in self._cache
        )

        recent_entries = self._cache[-10:] if len(self._cache) >= 10 else self._cache
        recent_hits = sum(1 for item in recent_entries if item.get("hit_count", 0) > 0)
        hit_rate_recent = recent_hits / len(recent_entries) if recent_entries else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_cache_size,
            "total_hits": total_hits,
            "similarity_threshold": self.similarity_threshold,
            "estimated_latency_savings_ms": round(latency_savings * 1000, 1),
            "estimated_tokens_saved": tokens_saved,
            "hit_rate_last_10": round(hit_rate_recent, 3),
            "top_cached_queries": [
                {"query": item["query"][:50], "hits": item.get("hit_count", 0)}
                for item in sorted(self._cache, key=lambda x: x.get("hit_count", 0), reverse=True)[:5]
            ],
        }

    def clear(self) -> None:
        """Limpia todo el cache."""
        self._cache = []
        if self.cache_path.exists():
            self.cache_path.unlink()

    def invalidate_intent(self, intent: str) -> int:
        """Invalida todas las entradas de un intent especifico."""
        original_size = len(self._cache)
        self._cache = [item for item in self._cache if item.get("intent") != intent]

        lines = []
        with open(self.cache_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filtered_lines = []
        for i, line in enumerate(lines):
            if i < original_size:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("intent") != intent:
                        filtered_lines.append(line)
                except json.JSONDecodeError:
                    continue

        with open(self.cache_path, "w", encoding="utf-8") as f:
            f.writelines(filtered_lines)

        return original_size - len(self._cache)
