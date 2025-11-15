from pydantic import BaseModel


# Pydantic model for the request body
class PrimeRequest(BaseModel):
    n: int
    
class PrimeJobResponse(BaseModel):
    message: str
    task_id: str
    
class HealthStatus(BaseModel):
    overall_status: str
    dependencies_status: dict[str, str]

class PingResponse(BaseModel):
    message: str
    
