import mysql.connector
import bcrypt
import jwt
import datetime

def get_connection():
    return mysql.connector.connect(
        host="98.86.9.11",
        user="root",
        password="Srii@773",
        database="date"
    )

def create_user_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            jwt_token TEXT
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

SECRET_KEY = "your_secret_key_here"

def signup(username, email, password):
    conn = get_connection()
    cursor = conn.cursor()

    payload = {
        "username": username,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, jwt_token) VALUES (%s, %s, %s, %s)",
            (username, email, password, token)
        )
        conn.commit()
        print(" User registered successfully with JWT:", token)
        return token
    except mysql.connector.Error as err:
        print(" Error:", err)
    finally:
        cursor.close()
        conn.close()

def login(username, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password, user["password"]):
        try:
            decoded = jwt.decode(user["jwt_token"], SECRET_KEY, algorithms=["HS256"])
            print(" Login successful. JWT is valid:", user["jwt_token"])
            return user["jwt_token"]
        except jwt.ExpiredSignatureError:
            print(" Token expired. Please sign up again.")
        except jwt.InvalidTokenError:
            print(" Invalid token. Please sign up again.")
    else:
        print(" Invalid username or password")
    return None

def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        print(" Token is valid. Payload:", decoded)
        return decoded
    except jwt.ExpiredSignatureError:
        print(" Token has expired")
    except jwt.InvalidTokenError:
        print(" Invalid token")
    return None

if __name__ == "__main__":
    create_user_table()

   
    token = login("username", "password")

    if token:
        verify_token(token)

    cursor.close()
    conn.close()
    
