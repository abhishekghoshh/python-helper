import os
from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded

# Get Redis URL from environment variables, default to localhost for local dev
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Initialize Celery
# Broker url is the message broker (Redis)
# Backend url is where task results are stored (also Redis)
celery_app = Celery(
    'tasks',
    broker=broker_url,
    backend=backend_url
)

@celery_app.task(name="tasks.find_primes_task", soft_time_limit=30)
def find_primes_task(n: int):
    """
    Finds all prime numbers up to n.
    This task has a soft time limit of 30 seconds.
    """
    try:
        def is_prime(num):
            """Helper function to check if a number is prime."""
            if num <= 1:
                return False
            # Check for factors from 2 up to the square root of the number
            for i in range(2, int(num**0.5) + 1):
                if num % i == 0:
                    return False
            return True

        prime_count = 0
        for num in range(1, n + 1):
            if is_prime(num):
                prime_count += 1
        
        return f"Found {prime_count} primes between 1 and {n}."
    
    except SoftTimeLimitExceeded:
        # This block executes if the task exceeds the 30-second limit
        return f"Task failed: Time limit (30s) exceeded for finding primes up to {n}."