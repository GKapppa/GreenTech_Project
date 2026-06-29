import json
from pathlib import Path
import numpy as np

from src.observability import (
    AnomalyDetector,
    ObservabilityLogger,
    compute_cosine_similarity,
    get_system_metrics,
)


def test_compute_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    v4 = [-1.0, 0.0, 0.0]

    assert abs(compute_cosine_similarity(v1, v2) - 1.0) < 1e-6
    assert abs(compute_cosine_similarity(v1, v3) - 0.0) < 1e-6
    assert abs(compute_cosine_similarity(v1, v4) - (-1.0)) < 1e-6


def test_get_system_metrics():
    metrics = get_system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_mb" in metrics
    assert "memory_percent" in metrics
    assert "num_threads" in metrics
    assert isinstance(metrics["cpu_percent"], float)
    assert isinstance(metrics["memory_mb"], float)
    assert metrics["num_threads"] >= 1


def test_observability_logger_saves_log(tmp_path):
    log_file = tmp_path / "obs_test.jsonl"
    logger = ObservabilityLogger(log_path=str(log_file))

    question = "Como instalar un inversor?"
    answer = "El inversor convierte corriente continua en alterna."
    intent = "consulta_tecnica"
    latencies = {"planner": 0.05, "retrieval": 0.25, "generation": 1.10, "security": 0.02, "total": 1.42}
    tokens = {"input_tokens": 1500, "output_tokens": 300, "total_tokens": 1800}
    relevance_score = 0.85
    security_alert = True

    record = logger.log_execution(
        question=question,
        answer=answer,
        intent=intent,
        latencies=latencies,
        tokens=tokens,
        status="success",
        relevance_score=relevance_score,
        security_alert=security_alert,
    )

    assert record["question"] == question
    assert record["intent"] == intent
    assert record["latencies"]["total"] == 1.42
    assert record["tokens"]["total_tokens"] == 1800
    assert record["relevance_score"] == relevance_score
    assert record["security_alert"] is True
    assert "estimated_cost_usd" in record
    assert record["estimated_cost_usd"] > 0
    assert "quality_score" in record
    assert "system_metrics" in record

    assert log_file.exists()
    logs = logger.load_logs()
    assert len(logs) == 1
    assert logs[0]["question"] == question
    assert logs[0]["intent"] == intent
    assert logs[0]["latencies"]["generation"] == 1.10


def test_observability_logger_quality_score():
    logger = ObservabilityLogger()

    quality_with_content = logger.calculate_answer_quality(
        answer="El inversor convierte corriente continua en alterna para uso domestico.",
        question="Que hace un inversor?"
    )
    assert quality_with_content["has_answer"] is True
    assert quality_with_content["quality_score"] > 0.5
    assert quality_with_content["completeness"] > 0

    quality_no_content = logger.calculate_answer_quality(
        answer="Lo siento, no tengo informacion sobre ese tema.",
        question="?"
    )
    assert quality_no_content["has_answer"] is False
    assert quality_no_content["quality_score"] < 0.5


def test_anomaly_detector_empty():
    detector = AnomalyDetector([])
    assert detector.detect_latency_outliers() == []
    assert detector.detect_error_patterns() == {}
    assert detector.calculate_percentiles() == {"p50": 0.0, "p95": 0.0, "p99": 0.0}


def test_anomaly_detector_with_logs(tmp_path):
    log_file = tmp_path / "obs_anomaly.jsonl"
    logger = ObservabilityLogger(log_path=str(log_file))

    for i in range(15):
        latencies = {
            "planner": 0.05,
            "retrieval": 0.2,
            "generation": 1.0 + (i * 0.1),
            "security": 0.02,
            "total": 1.27 + (i * 0.1),
        }
        status = "success" if i % 5 != 0 else "error"
        logger.log_execution(
            question=f"Pregunta {i}",
            answer=f"Respuesta {i}",
            intent="consulta_tecnica",
            latencies=latencies,
            tokens={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            status=status,
            relevance_score=0.8,
        )

    logs = logger.load_logs()
    detector = AnomalyDetector(logs)

    percentiles = detector.calculate_percentiles()
    assert percentiles["p50"] > 0
    assert percentiles["p95"] >= percentiles["p50"]

    error_patterns = detector.detect_error_patterns()
    assert "consulta_tecnica" in error_patterns

    error_rate = detector.calculate_error_rate(window_size=5)
    assert len(error_rate) >= 1

    recommendations = detector.get_recommendations()
    assert isinstance(recommendations, list)


def test_anomaly_detector_summary(tmp_path):
    log_file = tmp_path / "obs_summary.jsonl"
    logger = ObservabilityLogger(log_path=str(log_file))

    for i in range(10):
        logger.log_execution(
            question=f"Pregunta {i}",
            answer="Respuesta de prueba con contenido suficiente.",
            intent="consulta_tecnica",
            latencies={"planner": 0.05, "retrieval": 0.2, "generation": 1.0, "security": 0.02, "total": 1.27},
            tokens={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            status="success",
            relevance_score=0.85,
        )

    logs = logger.load_logs()
    detector = AnomalyDetector(logs)
    summary = detector.generate_summary()

    assert summary["total_queries"] == 10
    assert summary["success_count"] == 10
    assert summary["error_count"] == 0
    assert "percentiles" in summary
    assert "token_stats" in summary
