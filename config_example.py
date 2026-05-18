import psycopg2

def get_connection():
    params = {
        "dbname": "nutrition_tracker",
        "user": "your_username",
        "host": "127.0.0.1",
        "port": "5432",
        "password": "your_password"
    }

    return psycopg2.connect(**params)