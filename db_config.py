import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="98.86.9.11",
        user="root",
        password="Srii@773",
        database="datas"
    )

def create_user_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    
