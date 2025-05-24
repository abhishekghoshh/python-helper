# Python CRUD Celery App

This project is a Python application that implements a CRUD API for adding users to a MongoDB database. It utilizes Celery for asynchronous task processing and RabbitMQ as the message broker.

## Project Structure

```
python-crud-celery-app
├── app
│   ├── __init__.py
│   ├── api.py
│   ├── celery_worker.py
│   ├── models.py
│   ├── tasks.py
│   └── utils.py
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Technologies Used

- Python
- Flask or FastAPI (for the API)
- MongoDB (for the database)
- Celery (for task processing)
- RabbitMQ (for message brokering)

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd python-crud-celery-app
   ```

2. **Build and run the application using Docker Compose:**
   ```
   docker-compose up --build
   ```

3. **Access the API:**
   The API will be available at `http://localhost:5000` (or the port specified in your `docker-compose.yaml`).

## Usage

### Adding a User

To add a user, send a POST request to the `/add_user` endpoint with the user data in JSON format. For example:

```
POST /add_user
Content-Type: application/json

{
    "name": "John Doe",
    "email": "john.doe@example.com"
}
```

### Job Status

To check the status of a job, send a GET request to the `/job_status/<job_id>` endpoint.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.