
import threading

from fastapi import Depends, FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
from pytz import utc
import aiohttp

def create_job(id: int):
    return {
        "job_id": id,
        "counter": 0
    }
    
job1 = create_job(1)
job2 = create_job(2)

def job_service(id: int):
    if id == 1:
        return job1
    elif id == 2:
        return job2
    else:
        return None

def job_dependency():
    return job_service


def job1_counter():
    print("Current thread is", threading.current_thread().name, "and job id is", job1["job_id"],"counter is", job1["counter"])
    job1["counter"] = job1["counter"] + 1
    
def job2_counter():
    print("Current thread is", threading.current_thread().name, "and job id is", job2["job_id"],"counter is", job2["counter"])
    job2["counter"] = job2["counter"] + 1   

async def async_job2_counter():
    print("async func Current thread is", threading.current_thread().name, "and job id is", job2["job_id"],"counter is", job2["counter"])
    job2["counter"] = job2["counter"] + 1


async_scheduler = AsyncIOScheduler(timezone=utc)

@async_scheduler.scheduled_job('cron', second='*/15')
async def fetch_current_time():
    url = 'https://timeapi.io/api/Time/current/zone?timeZone=UTC'
    async with aiohttp.ClientSession() as session:
        try:
            r = await session.get(url)
            r.raise_for_status()
            print(f'TimeAPI result: {await r.json()}'," Current thread is", threading.current_thread().name)
        except aiohttp.ClientError as e:
            print(f'Error: {e}')

@asynccontextmanager
async def lifespan(_: FastAPI):
    print('app started....')
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(id="job1", func=job1_counter, trigger='cron', second='*/5')
    scheduler.add_job(id="job2", func=job2_counter, trigger='cron', second='*/10')
    scheduler.start()
    
    async_scheduler.add_job(id="job2_async", func=async_job2_counter, trigger='cron', second='*/10')
    async_scheduler.start()

    
    yield
    print('app stopped...')
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


# Add a get api with job status and job_dependency as dependency
@app.get("/async/job/{job_id}")
async def job_status(job_id: int, svc = Depends(job_dependency)):
    job = svc(job_id)
    print("Current thread is ", threading.current_thread().name, " and job id is ", job_id)
    if job is None:
        return {"error": "Job not found"}
    return job

@app.get("/sync/job/{job_id}")
def job_status(job_id: int, svc = Depends(job_dependency)):
    job = svc(job_id)
    print("Current thread is ", threading.current_thread().name, " and job id is ", job_id)
    if job is None:
        return {"error": "Job not found"}
    return job

if __name__ == "__main__":
    uvicorn.run("main:app")