
from fastapi import Depends, FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import uvicorn
import uuid
from datetime import datetime

counter = 1


async def job_dependency():
    job_id = str(uuid.uuid4())
    job_start_time = datetime.now().isoformat()
    return {
        "job_id": job_id,
        "job_start_time": job_start_time,
    }

def job_counter(job_config=Depends(job_dependency)):
    global counter
    print(f'cron job {type(job_config)}: call you https requests here...')
    counter = counter + 1


@asynccontextmanager
async def lifespan(_: FastAPI,job_config=Depends(job_dependency)):
    print('app started....')
    print(f'job_config: {job_config}')
    scheduler = BackgroundScheduler()
    scheduler.add_job(id="job1", func=job_counter, trigger='cron', second='*/2')
    scheduler.start()
    yield
    print('app stopped...')
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# Add a get api with job status and job_dependency as dependency
@app.get("/job_status")
async def job_status(job_config=Depends(job_dependency)):
    return {
        "job_id": job_config["job_id"],
        "job_start_time": job_config["job_start_time"],
        "counter": counter,
    }

if __name__ == "__main__":
    uvicorn.run("main:app")