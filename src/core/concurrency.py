"""
Concurrency primitives shared across the application.

pipeline_semaphore: caps the number of simultaneous RAG pipeline executions
on a single worker process. When all slots are taken, new tool calls suspend
(not block) the event loop until a slot frees up, preventing OOM and
downstream API rate-limit bursts.

Note: Each Uvicorn worker has its own semaphore. The total effective concurrency
across N workers is N × PIPELINE_MAX_CONCURRENT. Coordinate with RATE_LIMIT_PER_MINUTE
to keep total load within external API quotas (Cohere, OpenAI).
"""
import asyncio

from src.core.config import settings

pipeline_semaphore = asyncio.Semaphore(settings.PIPELINE_MAX_CONCURRENT)
