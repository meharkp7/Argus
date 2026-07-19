"""Embedding-based retrieval with reranking and citation discipline."""

from __future__ import annotations

import json
from typing import Any

import anthropic
import numpy as np

from backend.api.schemas import RAGCitation, RAGQueryResponse
from backend.config.settings import get_settings
from backend.rag.embeddings import EmbeddingEngine
from backend.rag.ingest import CorpusIngester, Document


class RAGRetriever:
    """Retrieves relevant documents and synthesizes cited answers."""

    SYSTEM_PROMPT = """You are ARGUS Incident Pattern Intelligence. Answer questions about industrial safety
incidents and regulations using ONLY the provided source documents.

Rules:
- ALWAYS cite specific source documents by title and clause reference
- NEVER invent incidents, regulations, or statistics not in the sources
- If no relevant source is found, say so explicitly
- Focus on pattern matching: how does the current situation relate to historical incidents
- Keep answers concise and actionable"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ingester = CorpusIngester()
        self.embedding_engine = EmbeddingEngine()
        self._client: anthropic.Anthropic | None = None

        if self.settings.anthropic_api_key:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

        if not self.ingester.load_index():
            self.ingester.ingest_all()

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
        alert_context: dict[str, Any] | None = None,
    ) -> RAGQueryResponse:
        k = top_k or self.settings.rag_top_k
        results = self._retrieve(query_text, k)

        if alert_context:
            context_query = f"{query_text} {json.dumps(alert_context, default=str)}"
            context_results = self._retrieve(context_query, k)
            seen_ids = {r[0].doc_id for r in results}
            for doc, score in context_results:
                if doc.doc_id not in seen_ids:
                    results.append((doc, score * 0.9))

        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:k]

        citations = [
            RAGCitation(
                document_id=doc.doc_id,
                title=doc.title,
                source=doc.source,
                excerpt=doc.content[:500],
                relevance_score=round(score, 3),
                clause_reference=doc.clause_reference,
            )
            for doc, score in results
            if score >= self.settings.rag_min_similarity
        ]

        answer = self._synthesize(query_text, results, alert_context)
        matched_patterns = self._extract_patterns(results)

        return RAGQueryResponse(
            query=query_text,
            answer=answer,
            citations=citations,
            matched_patterns=matched_patterns,
        )

    def _retrieve(
        self,
        query: str,
        top_k: int,
    ) -> list[tuple[Document, float]]:
        if not self.ingester.documents:
            return []

        query_embedding = self.embedding_engine.embed_single(query)
        scores: list[tuple[Document, float]] = []

        for i, doc in enumerate(self.ingester.documents):
            doc_embedding = np.array(self.ingester._embeddings[i])
            score = self.embedding_engine.similarity(query_embedding, doc_embedding)
            scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k * 2]

    def _synthesize(
        self,
        query: str,
        results: list[tuple[Document, float]],
        alert_context: dict[str, Any] | None,
    ) -> str:
        if not results:
            return "No relevant documents found in the corpus for this query."

        if self._client:
            try:
                return self._llm_synthesize(query, results, alert_context)
            except Exception:
                pass

        return self._template_synthesize(query, results)

    def _llm_synthesize(
        self,
        query: str,
        results: list[tuple[Document, float]],
        alert_context: dict[str, Any] | None,
    ) -> str:
        sources = []
        for doc, score in results[:5]:
            sources.append(
                {
                    "title": doc.title,
                    "framework": doc.framework,
                    "clause": doc.clause_reference,
                    "content": doc.content[:1500],
                    "relevance": score,
                }
            )

        context = {"query": query, "sources": sources}
        if alert_context:
            context["alert_context"] = alert_context

        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=800,
            system=self.SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Synthesize an answer:\n{json.dumps(context, indent=2, default=str)}",
                }
            ],
        )

        return response.content[0].text

    def _template_synthesize(
        self,
        query: str,
        results: list[tuple[Document, float]],
    ) -> str:
        parts = [f"Based on the ARGUS incident and regulatory corpus:"]

        for doc, score in results[:3]:
            if score < self.settings.rag_min_similarity:
                continue
            citation = f"[{doc.title}"
            if doc.clause_reference:
                citation += f", {doc.clause_reference}"
            citation += f", relevance: {score:.0%}]"

            excerpt = doc.content[:300].replace("\n", " ").strip()
            parts.append(f"\n{citation}: {excerpt}")

        if len(parts) == 1:
            return "No sufficiently relevant documents found for this query."

        return " ".join(parts)

    def _extract_patterns(
        self,
        results: list[tuple[Document, float]],
    ) -> list[str]:
        patterns = []
        for doc, score in results:
            if score >= self.settings.rag_min_similarity:
                if "pattern" in doc.content.lower() or "near-miss" in doc.content.lower():
                    patterns.append(doc.title)
                elif doc.metadata.get("category") == "incidents":
                    patterns.append(doc.title)
        return patterns[:5]

    def audit_compliance(self, document_text: str, frameworks: list[str]) -> dict:
        """Compliance gap detection against regulatory corpus."""
        gaps = []
        query = f"compliance requirements safety procedure {document_text[:500]}"
        results = self._retrieve(query, top_k=10)

        doc_lower = document_text.lower()
        for doc, score in results:
            if doc.framework not in frameworks and frameworks:
                continue
            if score < self.settings.rag_min_similarity:
                continue

            requirements = self._extract_requirements(doc.content)
            for req in requirements:
                keywords = req["keywords"]
                if not any(kw in doc_lower for kw in keywords):
                    gaps.append(
                        {
                            "gap_id": f"GAP-{doc.doc_id}-{req['id']}",
                            "severity": req.get("severity", "medium"),
                            "description": req["description"],
                            "regulatory_clause": doc.clause_reference or doc.title,
                            "framework": doc.framework,
                            "recommendation": req.get(
                                "recommendation",
                                f"Add compliance with: {req['description']}",
                            ),
                        }
                    )

        compliance_score = max(0, 1.0 - len(gaps) * 0.15)
        return {
            "gaps": gaps[:10],
            "compliance_score": round(compliance_score, 2),
            "summary": (
                f"Found {len(gaps)} compliance gaps across "
                f"{len(set(g.framework for g in [Document('', '', f, f, '') for f in frameworks]))} frameworks."
                if gaps
                else "No significant compliance gaps detected."
            ),
        }

    def _extract_requirements(self, content: str) -> list[dict]:
        requirements = []
        req_id = 0

        keyword_map = {
            "gas monitoring": {
                "keywords": ["gas monitor", "gas detection", "gas-free", "lel"],
                "description": "Continuous gas monitoring requirements",
                "severity": "high",
            },
            "hot work": {
                "keywords": ["hot work", "welding", "cutting", "grinding"],
                "description": "Hot work permit and safety requirements",
                "severity": "high",
            },
            "confined space": {
                "keywords": ["confined space", "entry permit", "ventilation"],
                "description": "Confined space entry procedures",
                "severity": "critical",
            },
            "emergency": {
                "keywords": ["emergency", "evacuation", "response plan"],
                "description": "Emergency response plan requirements",
                "severity": "high",
            },
            "ppe": {
                "keywords": ["ppe", "personal protective", "safety equipment"],
                "description": "Personal protective equipment requirements",
                "severity": "medium",
            },
            "training": {
                "keywords": ["training", "competency", "certification"],
                "description": "Worker training and competency requirements",
                "severity": "medium",
            },
        }

        content_lower = content.lower()
        for key, req in keyword_map.items():
            if key in content_lower:
                req_id += 1
                requirements.append({"id": str(req_id), **req})

        return requirements


_retriever: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
