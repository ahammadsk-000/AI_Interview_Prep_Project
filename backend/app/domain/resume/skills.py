"""Curated skills taxonomy + text extraction.

A pragmatic, dependency-free skill recognizer: canonical skill -> alias set,
grouped by category. Extraction uses word-boundary matching (case-insensitive)
so "Go" doesn't match "Google" and "C++"/"C#" are handled literally.

This is intentionally rule-based and deterministic (testable, no LLM needed).
Embedding-based fuzzy matching (SentenceTransformers + pgvector) is a later-phase
augmentation, not a replacement.
"""
from __future__ import annotations

import re

# category -> { canonical : (aliases...) }
TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "languages": {
        "Python": ("python",),
        "Java": ("java",),
        "JavaScript": ("javascript", "js"),
        "TypeScript": ("typescript", "ts"),
        "Go": ("golang", "go"),
        "C++": ("c++", "cpp"),
        "C#": ("c#", "csharp"),
        "Rust": ("rust",),
        "SQL": ("sql",),
        "Bash": ("bash", "shell scripting"),
        "Scala": ("scala",),
        "R": (r"\br\b",),  # matched as a raw pattern (see _compile)
    },
    "ai_ml": {
        "Machine Learning": ("machine learning", "ml"),
        "Deep Learning": ("deep learning",),
        "NLP": ("nlp", "natural language processing"),
        "Computer Vision": ("computer vision", "cv"),
        "PyTorch": ("pytorch",),
        "TensorFlow": ("tensorflow",),
        "scikit-learn": ("scikit-learn", "sklearn"),
        "LangChain": ("langchain",),
        "LangGraph": ("langgraph",),
        "LlamaIndex": ("llamaindex", "llama-index"),
        "RAG": ("rag", "retrieval augmented generation", "retrieval-augmented generation"),
        "LLM": ("llm", "large language model", "large language models"),
        "Transformers": ("transformers", "hugging face", "huggingface"),
        "Vector Databases": ("vector database", "vector db", "pgvector", "pinecone", "faiss"),
    },
    "data": {
        "Pandas": ("pandas",),
        "NumPy": ("numpy",),
        "Spark": ("spark", "pyspark", "apache spark"),
        "Airflow": ("airflow",),
        "ETL": ("etl",),
        "Data Engineering": ("data engineering",),
        "Snowflake": ("snowflake",),
        "dbt": ("dbt",),
    },
    "backend": {
        "FastAPI": ("fastapi",),
        "Django": ("django",),
        "Flask": ("flask",),
        "Node.js": ("node.js", "nodejs", "node"),
        "Spring": ("spring", "spring boot"),
        "REST": ("rest", "rest api", "restful"),
        "GraphQL": ("graphql",),
        "gRPC": ("grpc",),
        "Microservices": ("microservices", "microservice"),
    },
    "frontend": {
        "React": ("react", "react.js", "reactjs"),
        "Next.js": ("next.js", "nextjs"),
        "Vue": ("vue", "vue.js"),
        "TailwindCSS": ("tailwind", "tailwindcss"),
    },
    "databases": {
        "PostgreSQL": ("postgresql", "postgres"),
        "MySQL": ("mysql",),
        "MongoDB": ("mongodb", "mongo"),
        "Redis": ("redis",),
        "Elasticsearch": ("elasticsearch", "elastic search"),
    },
    "devops_cloud": {
        "Docker": ("docker",),
        "Kubernetes": ("kubernetes", "k8s"),
        "AWS": ("aws", "amazon web services"),
        "GCP": ("gcp", "google cloud"),
        "Azure": ("azure",),
        "Terraform": ("terraform",),
        "CI/CD": ("ci/cd", "cicd", "continuous integration"),
        "GitHub Actions": ("github actions",),
        "Prometheus": ("prometheus",),
        "Grafana": ("grafana",),
    },
}

# Flatten to canonical -> (category, compiled_pattern)
_CANON_CATEGORY: dict[str, str] = {}
_PATTERNS: dict[str, re.Pattern[str]] = {}


def _compile(aliases: tuple[str, ...]) -> re.Pattern[str]:
    parts: list[str] = []
    for a in aliases:
        if a.startswith(r"\b"):  # already a raw regex (e.g. lone "R")
            parts.append(a)
        else:
            # Escape, then require word-ish boundaries that still allow +, #, .
            parts.append(rf"(?<![\w]){re.escape(a)}(?![\w])")
    return re.compile("|".join(parts), re.IGNORECASE)


for _category, _skills in TAXONOMY.items():
    for _canon, _aliases in _skills.items():
        _CANON_CATEGORY[_canon] = _category
        _PATTERNS[_canon] = _compile(_aliases)


ALL_SKILLS: tuple[str, ...] = tuple(_CANON_CATEGORY.keys())


def category_of(skill: str) -> str | None:
    return _CANON_CATEGORY.get(skill)


def extract_skills(text: str) -> set[str]:
    """Return the set of canonical skills mentioned in ``text``."""
    if not text:
        return set()
    return {canon for canon, pat in _PATTERNS.items() if pat.search(text)}
