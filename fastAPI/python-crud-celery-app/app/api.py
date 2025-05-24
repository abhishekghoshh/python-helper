from flask import Flask, request, jsonify
from celery import Celery
from pymongo import MongoClient
from bson import ObjectId
import os

app = Flask(__name__)
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://mongo:27017/jobs_db')
client = MongoClient(app.config['MONGO_URI'])
db = client.jobs_db
jobs_collection = db.jobs

celery = Celery(app.name, broker=os.getenv('BROKER_URL', 'pyamqp://guest@rabbit//'))

@app.route('/jobs', methods=['POST'])
def create_job():
    data = request.json
    if not data or 'user' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    job = jobs_collection.insert_one({'user': data['user'], 'status': 'pending'})
    job_id = str(job.inserted_id)
    
    # Send job to Celery worker
    process_job.delay(job_id)
    
    return jsonify({'job_id': job_id}), 201

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({'job_id': job_id, 'status': job['status']}), 200

@celery.task
def process_job(job_id):
    jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'completed'}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)