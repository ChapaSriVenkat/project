import mysql.connector
import jwt
import datetime

def get_connection():
    return mysql.connector.connect(
        host="35.169.16.216",
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

    # Store password directly (plain text)
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

    if user:
        if password == user["password"]:  # Direct string comparison
            try:
                decoded = jwt.decode(user["jwt_token"], SECRET_KEY, algorithms=["HS256"])
                print(" Login successful. JWT is valid:", user["jwt_token"])
                return user["jwt_token"]
            except jwt.ExpiredSignatureError:
                print(" Token expired. Generating new token...")
                # Generate new token
                payload = {
                    "username": username,
                    "email": user["email"],
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
                }
                new_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

                # Update DB
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET jwt_token=%s WHERE username=%s", (new_token, username))
                conn.commit()
                cursor.close()
                conn.close()

                return new_token
            except jwt.InvalidTokenError:
                print(" Invalid token. Please sign up again.")
        else:
            print(" Invalid password")
    else:
        print(" Invalid username")
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

    # Example run
    signup("plainuser", "plain@example.com", "mypassword123")
    token = login("plainuser", "mypassword123")
    if token:
        verify_token(token)
