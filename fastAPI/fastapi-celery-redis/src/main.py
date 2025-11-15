import asyncio
from fastapi import FastAPI
from celery.result import AsyncResult
from models import HealthStatus, PingResponse, PrimeJobResponse, PrimeRequest
from tasks import celery_app, find_primes_task

app = FastAPI(
    title="FastAPI Prime Finder with Celery",
    description="An API for finding prime numbers using Celery background tasks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ping api
@app.get("/ping")
async def ping() -> PingResponse:
    return {"message": "pong"}

# Health check api
@app.get("/health")
async def health_check() -> HealthStatus:
    # check redis status
    # check celery worker status
    try:
        redis_status = await asyncio.to_thread(celery_app.backend.client.ping)
        worker_status = await asyncio.to_thread(celery_app.control.ping, timeout=1.0)
    except Exception:
        redis_status = False
        worker_status = []
    
    dependencies_status = {
        "redis": "available" if redis_status else "unavailable",
        "celery_worker": "available" if worker_status else "unavailable"
    }
    overall_status = "healthy" if all(status == "available" for status in dependencies_status.values()) else "unhealthy"
    return HealthStatus(
        overall_status=overall_status,
        dependencies_status=dependencies_status
    )

@app.post("/submit-job", status_code=202)
async def submit_prime_job(request: PrimeRequest)-> PrimeJobResponse:
    """
    Submits a prime-finding job to the Celery queue.
    The user provides 'n', the upper limit for the prime search.
    """
    if request.n <= 0:
        return {"error": "n must be a positive integer"}
    
    # Send the task to the Celery queue
    task = find_primes_task.delay(request.n)
    
    return {"message": "Job submitted", "task_id": task.id}


@app.get("/job-status/{task_id}")
async def get_job_status(task_id: str):
    """
    Retrieves the status and result of a Celery task
    using its task_id.
    """
    # Get the task result from the backend (Redis)
    task_result = AsyncResult(task_id, app=celery_app)
    
    status = task_result.status
    result = None
    
    if task_result.successful():
        result = task_result.get()  # Get the return value
    elif status == 'FAILURE':
        # Get the exception/error message
        result = str(task_result.info) 
    
    return {
        "task_id": task_id,
        "status": status,
        "result": result
    }