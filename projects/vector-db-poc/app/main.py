from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Vector DB POC",
    description="A proof-of-concept FastAPI service exposing vector embedding and vector search APIs backed by Qdrant.",
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Vector DB POC", "docs": "/docs", "api": "/api/v1"}
