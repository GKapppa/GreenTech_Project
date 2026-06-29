import json
from pathlib import Path

import pytest

from src.cache import SemanticCache


def test_semantic_cache_initialization(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path), similarity_threshold=0.90)

    assert cache.similarity_threshold == 0.90
    assert cache.max_cache_size == 500
    assert cache_path.exists() is False


def test_semantic_cache_add_and_get(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path), similarity_threshold=0.90)

    query = "Como instalar paneles solares?"
    answer = "Para instalar paneles solares necesitas..."

    cache.add(
        query=query,
        answer=answer,
        intent="consulta_tecnica",
        latency=1.5,
        tokens_used=500,
        relevance_score=0.85,
    )

    assert len(cache._cache) == 1
    assert cache._cache[0]["query"] == query
    assert cache._cache[0]["answer"] == answer


def test_semantic_cache_hit(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path), similarity_threshold=0.85)

    query = "Que es el efecto fotoelectrico?"
    answer = "El efecto fotoelectrico es..."

    cache.add(
        query=query,
        answer=answer,
        intent="consulta_tecnica",
        latency=2.0,
        tokens_used=300,
    )

    cached_answer, metadata = cache.get(query)

    assert cached_answer == answer
    assert metadata["cache_hit"] is True
    assert metadata["similarity"] > 0.85


def test_semantic_cache_miss(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path), similarity_threshold=0.95)

    cached_answer, metadata = cache.get("Una consulta completamente diferente")

    assert cached_answer is None
    assert metadata["cache_hit"] is False


def test_semantic_cache_eviction(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(
        cache_path=str(cache_path),
        similarity_threshold=0.90,
        max_cache_size=3,
    )

    for i in range(5):
        cache.add(
            query=f"Consulta numero {i}",
            answer=f"Respuesta numero {i}",
            intent="consulta_tecnica",
            latency=1.0,
            tokens_used=100,
        )

    assert len(cache._cache) == 3


def test_semantic_cache_stats(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path), similarity_threshold=0.90)

    cache.add(
        query="Pregunta 1",
        answer="Respuesta 1",
        intent="consulta_tecnica",
        latency=1.5,
        tokens_used=200,
    )

    cache.get("Pregunta 1")
    cache.get("Pregunta 1")

    stats = cache.get_stats()

    assert stats["size"] == 1
    assert stats["total_hits"] == 2
    assert stats["estimated_latency_savings_ms"] > 0


def test_semantic_cache_clear(tmp_path):
    cache_path = tmp_path / "test_cache.jsonl"
    cache = SemanticCache(cache_path=str(cache_path))

    cache.add(
        query="Test query",
        answer="Test answer",
        intent="consulta_simple",
        latency=1.0,
        tokens_used=50,
    )

    assert len(cache._cache) == 1
    cache.clear()
    assert len(cache._cache) == 0
    assert not cache_path.exists()
