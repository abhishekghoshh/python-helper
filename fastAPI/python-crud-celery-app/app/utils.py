def validate_user_data(data):
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary.")
    
    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(data['name'], str) or not isinstance(data['email'], str):
        raise ValueError("Name and email must be strings.")
    
    return True

def format_response(message, status_code):
    return {
        "message": message,
        "status_code": status_code
    }