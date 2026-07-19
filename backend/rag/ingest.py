"""Document ingestion pipeline for regulatory and incident corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config.settings import CORPUS_DIR, VECTOR_STORE_PATH
from backend.rag.embeddings import EmbeddingEngine


@dataclass
class Document:
    doc_id: str
    title: str
    source: str
    framework: str
    content: str
    clause_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CorpusIngester:
    """Ingests and indexes regulatory and incident documents."""

    def __init__(self, corpus_dir: Path | None = None) -> None:
        self.corpus_dir = corpus_dir or CORPUS_DIR
        self.embedding_engine = EmbeddingEngine()
        self.documents: list[Document] = []
        self._embeddings: list[Any] = []
        self._index_path = VECTOR_STORE_PATH / "corpus_index.json"

    def ingest_all(self) -> int:
        self.documents = []
        count = 0

        for subdir in ["regulations", "incidents"]:
            dir_path = self.corpus_dir / subdir
            if not dir_path.exists():
                continue
            for file_path in sorted(dir_path.glob("*.md")):
                doc = self._parse_markdown(file_path, subdir)
                if doc:
                    self.documents.append(doc)
                    count += 1
            for file_path in sorted(dir_path.glob("*.json")):
                doc = self._parse_json(file_path, subdir)
                if doc:
                    self.documents.append(doc)
                    count += 1

        if self.documents:
            texts = [d.content for d in self.documents]
            self._embeddings = self.embedding_engine.embed(texts).tolist()
            self._save_index()

        return count

    def _parse_markdown(self, path: Path, category: str) -> Document | None:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return None

        title = path.stem.replace("_", " ").title()
        framework = "OISD"
        clause = None

        for line in text.split("\n")[:10]:
            if line.startswith("# "):
                title = line[2:].strip()
            if "Framework:" in line:
                framework = line.split("Framework:")[-1].strip()
            if "Clause:" in line:
                clause = line.split("Clause:")[-1].strip()

        return Document(
            doc_id=path.stem,
            title=title,
            source=path.name,
            framework=framework,
            content=text,
            clause_reference=clause,
            metadata={"category": category, "file": str(path.name)},
        )

    def _parse_json(self, path: Path, category: str) -> Document | None:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Document(
            doc_id=data.get("id", path.stem),
            title=data.get("title", path.stem),
            source=path.name,
            framework=data.get("framework", "General"),
            content=data.get("content", json.dumps(data)),
            clause_reference=data.get("clause_reference"),
            metadata={"category": category, **data.get("metadata", {})},
        )

    def _save_index(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        index_data = {
            "documents": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "source": d.source,
                    "framework": d.framework,
                    "content": d.content,
                    "clause_reference": d.clause_reference,
                    "metadata": d.metadata,
                }
                for d in self.documents
            ],
            "embeddings": self._embeddings,
        }
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

    def load_index(self) -> bool:
        if not self._index_path.exists():
            return False

        with open(self._index_path, encoding="utf-8") as f:
            data = json.load(f)

        self.documents = [
            Document(**{k: v for k, v in d.items() if k != "metadata"} | {"metadata": d.get("metadata", {})})
            for d in data["documents"]
        ]
        self._embeddings = data["embeddings"]
        return True
