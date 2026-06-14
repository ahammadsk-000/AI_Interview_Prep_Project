"""Seeded interview question bank (deterministic fallback for the AI engine).

When an LLM backend is unavailable (offline/tests) the engine draws from this
curated bank, preferring the current difficulty and never repeating a question
already asked in the session. With an LLM the bank seeds and grounds generation.
"""
from __future__ import annotations

from app.domain.interview.enums import Difficulty, InterviewType

D = Difficulty
T = InterviewType

# type -> list[(difficulty, question)]
BANK: dict[InterviewType, list[tuple[Difficulty, str]]] = {
    T.HR: [
        (D.EASY, "Tell me about yourself and what brings you to this role."),
        (D.EASY, "What are your greatest strengths, and how do they apply here?"),
        (D.MEDIUM, "Describe a time you faced conflict on a team and how you handled it."),
        (D.MEDIUM, "Why do you want to leave your current role and join us?"),
        (D.HARD, "Tell me about a significant failure and what you learned from it."),
        (D.HARD, "Where do you see yourself in five years, and how does this role fit?"),
    ],
    T.TECHNICAL: [
        (D.EASY, "Walk me through a project you're proud of and your specific contribution."),
        (D.MEDIUM, "How do you ensure code quality and reliability in production systems?"),
        (D.MEDIUM, "Explain the difference between processes and threads, with a use case."),
        (D.HARD, "Design an idempotent API for processing payments; what edge cases worry you?"),
        (D.HARD, "How would you debug a service whose p99 latency suddenly tripled?"),
    ],
    T.SYSTEM_DESIGN: [
        (D.EASY, "What factors do you weigh when choosing a database for a new service?"),
        (D.MEDIUM, "Design a URL shortener. Walk me through the data model and scaling."),
        (D.HARD, "Design a globally distributed rate limiter. How do you handle consistency?"),
        (D.HARD, "Design a news feed for 100M users. Discuss fan-out and caching trade-offs."),
    ],
    T.ML: [
        (D.EASY, "Explain the bias-variance trade-off with a concrete example."),
        (D.MEDIUM, "How do you handle class imbalance in a fraud-detection model?"),
        (D.MEDIUM, "Your model performs well offline but poorly in production. How do you debug?"),
        (D.HARD, "Design an end-to-end ML system for real-time recommendations."),
    ],
    T.GENAI: [
        (D.EASY, "What is retrieval-augmented generation and when would you use it?"),
        (D.MEDIUM, "How would you reduce hallucinations in an LLM-based assistant?"),
        (D.MEDIUM, "Compare fine-tuning vs RAG vs prompt engineering for a domain task."),
        (D.HARD, "Design an evaluation harness for a multi-agent LLM system in production."),
    ],
    T.DEVOPS: [
        (D.EASY, "Walk me through a CI/CD pipeline you have built or operated."),
        (D.MEDIUM, "How do you achieve zero-downtime deployments on Kubernetes?"),
        (D.HARD, "A production rollout is failing intermittently. Describe your incident response."),
    ],
    T.PM: [
        (D.EASY, "How do you prioritize a backlog with limited engineering capacity?"),
        (D.MEDIUM, "Tell me about a product decision you made that the data later contradicted."),
        (D.HARD, "How would you define success metrics for an AI interview-prep product?"),
    ],
}

GENERIC_FOLLOW_UPS = (
    "Can you go deeper on the most challenging part of that?",
    "What trade-offs did you consider, and why did you choose that approach?",
    "How did you measure the impact of that work?",
    "If you had to do it again, what would you change?",
)


# Technology-specific questions keyed by the *canonical* skill names from
# ``app.domain.resume.skills`` so they can be selected from a candidate's résumé.
SKILL_QUESTIONS: dict[str, tuple[str, ...]] = {
    "Python": (
        "Explain the difference between a list, a tuple, and a set, and when you'd use each.",
        "What are Python generators and when would you prefer them over a list?",
        "How does the Global Interpreter Lock (GIL) affect multithreaded Python?",
        "Explain decorators with a concrete example of where you've used one.",
        "What is the difference between deepcopy and a shallow copy?",
        "How does Python manage memory and garbage collection?",
        "What are context managers and how do you write one?",
        "Explain *args and **kwargs and a real use case.",
        "How would you profile and optimize a slow Python function?",
        "What is the difference between asyncio and threading, and when to use each?",
    ),
    "FastAPI": (
        "How does FastAPI use Python type hints for validation and docs?",
        "Explain dependency injection in FastAPI with an example.",
        "How do you handle authentication and authorization in FastAPI?",
        "Sync vs async path operations in FastAPI — when does each matter?",
        "How would you structure a large FastAPI project for maintainability?",
        "How do you do background tasks and long-running work in FastAPI?",
    ),
    "Django": (
        "Explain Django's MVT architecture.",
        "What is the Django ORM and what are its limits for complex queries?",
        "How do migrations work in Django and how do you handle conflicts?",
        "How do you optimize a slow Django view that hits the database too often?",
        "Explain Django middleware and a case where you'd write custom middleware.",
    ),
    "Flask": (
        "How does Flask differ from Django, and when would you choose it?",
        "What are Flask blueprints and why use them?",
        "How do you manage application and request context in Flask?",
        "How would you add async or background processing to a Flask app?",
    ),
    "SQL": (
        "Explain the difference between INNER, LEFT, and FULL OUTER joins.",
        "What is an index and how does it speed up queries — what's the cost?",
        "How would you find and fix a slow query?",
        "Explain ACID properties and transaction isolation levels.",
        "What is N+1 query problem and how do you avoid it?",
        "Window functions vs GROUP BY — give an example where you need a window function.",
    ),
    "PostgreSQL": (
        "What PostgreSQL features have you used beyond basic CRUD (JSONB, CTEs, etc.)?",
        "How does indexing differ for B-tree vs GIN vs GiST indexes?",
        "How would you scale PostgreSQL reads and writes?",
        "Explain MVCC and how PostgreSQL handles concurrent writes.",
    ),
    "MongoDB": (
        "When would you choose MongoDB over a relational database?",
        "How do you model relationships in a document database?",
        "What are the trade-offs of embedding vs referencing documents?",
        "How does indexing and sharding work in MongoDB?",
    ),
    "Redis": (
        "What are common use cases for Redis in a backend system?",
        "Explain Redis data structures you've used and why.",
        "How would you implement rate limiting or caching with Redis?",
        "What happens when Redis runs out of memory, and how do you handle persistence?",
    ),
    "REST": (
        "What makes an API RESTful, and where do real APIs deviate?",
        "How do you version a REST API without breaking clients?",
        "Explain idempotency and which HTTP methods should be idempotent.",
        "How do you design pagination, filtering, and error responses?",
    ),
    "GraphQL": (
        "What problems does GraphQL solve compared to REST?",
        "What is the N+1 problem in GraphQL and how do dataloaders help?",
        "How do you handle authorization in a GraphQL API?",
    ),
    "Microservices": (
        "What are the trade-offs of microservices vs a modular monolith?",
        "How do services communicate, and how do you handle failures between them?",
        "How do you manage data consistency across services?",
        "How do you handle distributed tracing and observability?",
    ),
    "Docker": (
        "What is the difference between an image and a container?",
        "How do you reduce Docker image size and build time?",
        "Explain multi-stage builds and why they're useful.",
        "How do containers differ from virtual machines?",
        "How do you handle secrets and configuration in containers?",
    ),
    "Kubernetes": (
        "Explain Pods, Deployments, and Services in Kubernetes.",
        "How does Kubernetes handle scaling and self-healing?",
        "What is the difference between a readiness and a liveness probe?",
        "How would you do a zero-downtime deployment on Kubernetes?",
        "How do you manage configuration and secrets in Kubernetes?",
    ),
    "AWS": (
        "Which AWS services have you used and for what?",
        "Explain the difference between EC2, ECS/EKS, and Lambda.",
        "How do you secure access in AWS (IAM roles, least privilege)?",
        "How would you design a highly available system on AWS?",
    ),
    "CI/CD": (
        "Walk me through a CI/CD pipeline you have built or operated.",
        "How do you ensure tests, linting, and security checks gate a deploy?",
        "How do you do safe rollbacks when a release breaks production?",
    ),
    "JavaScript": (
        "Explain closures with a practical example.",
        "What is the event loop and how does async work in JavaScript?",
        "Difference between var, let, and const.",
        "Explain promises vs async/await and error handling.",
        "What is prototypal inheritance?",
    ),
    "TypeScript": (
        "What problems does TypeScript solve over plain JavaScript?",
        "Explain generics with a real use case.",
        "What is the difference between type and interface?",
        "How do you type an async API response safely?",
    ),
    "React": (
        "Explain the virtual DOM and reconciliation.",
        "What are hooks, and what problem do useEffect and useMemo solve?",
        "How do you manage state in a large React app?",
        "How do you optimize React rendering performance?",
        "Explain controlled vs uncontrolled components.",
    ),
    "Node.js": (
        "How does Node's non-blocking I/O model work?",
        "How do you handle CPU-bound work in Node.js?",
        "Explain streams and when you'd use them.",
        "How do you structure error handling in an Express/Node API?",
    ),
    "Machine Learning": (
        "Explain the bias-variance trade-off with an example.",
        "How do you handle class imbalance in a classifier?",
        "How do you prevent overfitting?",
        "Walk me through how you'd evaluate a model beyond accuracy.",
        "How do you handle missing data and feature scaling?",
        "Your model is great offline but poor in production — how do you debug it?",
    ),
    "Deep Learning": (
        "Explain backpropagation at a high level.",
        "What are vanishing/exploding gradients and how do you mitigate them?",
        "When would you use a CNN vs an RNN vs a Transformer?",
        "How do batch normalization and dropout help training?",
    ),
    "NLP": (
        "What are embeddings and why are they useful?",
        "Explain tokenization and why it matters for LLMs.",
        "How would you build a text classification pipeline?",
        "What evaluation metrics fit an NLP task you've worked on?",
    ),
    "PyTorch": (
        "Explain the difference between PyTorch tensors and NumPy arrays.",
        "What is autograd and how does it work?",
        "Walk me through a typical PyTorch training loop.",
        "How do you move computation to GPU and debug memory issues?",
    ),
    "TensorFlow": (
        "Eager execution vs graph mode in TensorFlow — trade-offs?",
        "How do you build and serve a model with TensorFlow?",
        "How do you debug a model that isn't converging?",
    ),
    "LLM": (
        "How would you reduce hallucinations in an LLM application?",
        "Compare prompt engineering, RAG, and fine-tuning for a domain task.",
        "How do you evaluate the quality of an LLM's outputs?",
        "How do you control cost and latency in an LLM-powered feature?",
        "How do you handle prompt injection and safety?",
    ),
    "RAG": (
        "Explain the RAG architecture end to end.",
        "How do you chunk and embed documents for good retrieval?",
        "How do you evaluate and improve retrieval quality?",
        "When does RAG fail, and how do you detect it?",
    ),
    "LangChain": (
        "What problems does LangChain solve and what are its trade-offs?",
        "How do you build an agent with tools using LangChain?",
        "How do you add memory and tracing to a LangChain app?",
    ),
    "Pandas": (
        "How do you handle a dataset too large to fit in memory with pandas?",
        "Explain the difference between merge, join, and concat.",
        "How do you vectorize an operation instead of looping?",
        "How do you detect and handle missing or duplicate data?",
    ),
    "Spark": (
        "Explain how Spark distributes work across a cluster.",
        "What is the difference between transformations and actions?",
        "How do you handle data skew and shuffles in Spark?",
    ),
    "Java": (
        "Explain the difference between an interface and an abstract class.",
        "How does garbage collection work in the JVM?",
        "What are checked vs unchecked exceptions?",
        "Explain the Java memory model and concurrency basics.",
    ),
    "Go": (
        "Explain goroutines and channels.",
        "How does Go handle concurrency differently from threads?",
        "What is the difference between a slice and an array in Go?",
        "How does error handling work idiomatically in Go?",
    ),
}


def questions_for(interview_type: InterviewType) -> list[tuple[Difficulty, str]]:
    return BANK.get(interview_type, BANK[InterviewType.TECHNICAL])


def questions_for_skills(skills: list[str]) -> list[str]:
    """Flatten skill-specific questions for the given canonical skills (order preserved)."""
    out: list[str] = []
    for skill in skills:
        out.extend(SKILL_QUESTIONS.get(skill, ()))
    return out
