import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LongTermMemoryStore:
    def __init__(self, path: str = "data/memory/long_term_memory.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def save_interaction(self, question: str, answer: str, intent: str) -> None:
        memories = self.load()
        memories.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "intent": intent,
                "question": question,
                "answer_summary": answer[:500],
            }
        )
        self.path.write_text(json.dumps(memories[-50:], indent=2, ensure_ascii=False), encoding="utf-8")

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        scored_memories = []

        for memory in self.load():
            memory_text = f"{memory.get('question', '')} {memory.get('answer_summary', '')}".lower()
            score = sum(1 for term in query_terms if term in memory_text)
            if score > 0:
                scored_memories.append((score, memory))

        scored_memories.sort(key=lambda item: item[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]

    def format_relevant_memories(self, query: str) -> str:
        memories = self.search(query)
        if not memories:
            return "No hay memoria larga relevante para esta consulta."

        return "\n".join(
            f"- [{memory.get('intent')}] {memory.get('question')} -> {memory.get('answer_summary')}"
            for memory in memories
        )
