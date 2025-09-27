import streamlit as st
from db_config import get_connection, create_user_table
from gtts import gTTS
import os
import time
import docx
import fitz
import jwt
import datetime

SECRET_KEY = "your_secret_key_here"

st.set_page_config(page_title="Text to Speech App", layout="wide")

create_user_table()

STORAGE_DIR = "user_files"
os.makedirs(STORAGE_DIR, exist_ok=True)



def signup(username, email, password):
    """Create user and store raw password in DB (insecure; for testing only)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    existing_user = cursor.fetchone()

    if existing_user:
        if existing_user[1] == username:
            st.error(" Username already exists. Please choose another.")
        elif existing_user[2] == email:
            st.error(" Email already registered. Please log in instead.")
    else:
        token = jwt.encode(
            {"username": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            SECRET_KEY,
            algorithm="HS256"
        )

        if isinstance(token, bytes):
            token = token.decode("utf-8")

        cursor.execute(
            "INSERT INTO users (username, email, password, Jwt) VALUES (%s,%s,%s,%s)",
            (username, email, password, token)
        )
        conn.commit()

        st.success(" Signup successful! Please log in.")
        st.session_state["page"] = "Login"

    cursor.close()
    conn.close()


def login(username, password):
    """Authenticate using raw password comparison (insecure; for testing only)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password, Jwt FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()

    if user and password == user[3]:  
        token = jwt.encode(
            {"username": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
            SECRET_KEY,
            algorithm="HS256"
        )

        if isinstance(token, bytes):
            token = token.decode("utf-8")

        cursor.execute("UPDATE users SET Jwt=%s WHERE id=%s", (token, user[0]))
        conn.commit()

        cursor.close()
        conn.close()
        return user, token
    else:
        cursor.close()
        conn.close()
        return None, None


def verify_token(token):
    """Verify JWT token and return username if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except jwt.ExpiredSignatureError:
        st.error("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        st.error("Invalid token.")
    return None



def extract_text(uploaded_file):
    """Extract text from txt, pdf, or docx"""
    ext = os.path.splitext(uploaded_file.name)[-1].lower()

    if ext == ".txt":
        return uploaded_file.read().decode("utf-8")

    elif ext == ".pdf":
        text = ""
        pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in pdf_doc:
            text += page.get_text()
        return text

    elif ext == ".docx":
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        return None



if "page" not in st.session_state:
    st.session_state["page"] = "Signup"

st.title("Text-to-Speech App")

if st.session_state["page"] == "Signup":
    st.subheader("Create Account")
    new_user = st.text_input("Username", key="signup_user")
    new_email = st.text_input("Email", key="signup_email")
    new_pass = st.text_input("Password ", type="password", key="signup_pass")

    if st.button("Sign Up"):
        if new_user and new_email and new_pass:
            signup(new_user, new_email, new_pass)
        else:
            st.warning("Please fill in all fields.")

    if st.button("Already have an account? Login"):
        st.session_state["page"] = "Login"
        st.rerun()

elif st.session_state["page"] == "Login":
    st.subheader("Login with Username/Password")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        user, token = login(username, password)
        if user:
            st.session_state["user"] = username
            st.session_state["token"] = token
            st.session_state["page"] = "Dashboard"
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials.")

    st.divider()

    st.subheader("Login with JWT Token")
    jwt_token = st.text_input("Enter JWT Token", key="login_token")

    if st.button("Login with Token"):
        username = verify_token(jwt_token)
        if username:
            st.session_state["user"] = username
            st.session_state["token"] = jwt_token
            st.session_state["page"] = "Dashboard"
            st.success(f"Welcome back, {username}!")
            st.rerun()

    if st.button("Don't have an account? Sign Up"):
        st.session_state["page"] = "Signup"
        st.rerun()

elif st.session_state["page"] == "Dashboard":
    if "user" in st.session_state:
        username = st.session_state["user"]
        token = st.session_state.get("token", "No Token Found")
        st.subheader(f"Welcome, {username}")
        st.caption(f"Your JWT: {token}")

        user_dir = os.path.join(STORAGE_DIR, username)
        os.makedirs(user_dir, exist_ok=True)

        uploaded_files = st.file_uploader(
            "Upload text/PDF/DOCX files",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=True
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                extract_start = time.time()
                text = extract_text(uploaded_file)
                extract_end = time.time()
                extraction_time = round(extract_end - extract_start, 2)

                if not text:
                    st.error(f" Could not read {uploaded_file.name}")
                    continue

                st.text_area(
                    f"{uploaded_file.name}",
                    text[:2000],
                    height=150,
                    key=f"text_{uploaded_file.name}"
                )
                st.caption(f" Text extraction completed in {extraction_time} seconds")

                if st.button(f"Convert {uploaded_file.name}", key=f"convert_{uploaded_file.name}"):
                    timestamp = int(time.time())
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    audio_filename = f"{base_name}_{timestamp}.mp3"
                    audio_file_path = os.path.join(user_dir, audio_filename)

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    est_time = max(1, len(text) // 500)
                    st.info(f" Estimated conversion time: {est_time + 5} miutes ")

                    conv_start = time.time()
                    with st.spinner(" Converting text to speech... Please wait"):
                        tts = gTTS(text=text, lang="en")
                        tts.save(audio_file_path)
                    conv_end = time.time()
                    conversion_time = round(conv_end - conv_start, 2)

                    steps = 100
                    for i in range(steps + 1):
                        time.sleep(conversion_time / steps if conversion_time > 0 else 0.01)
                        progress_bar.progress(i)
                        status_text.text(
                            f" {i}% | Time Remaining: {round((conversion_time/steps)*(steps-i),1)}s"
                        )

                    status_text.text(f" Conversion completed in {conversion_time}s")

                    st.success(f" File converted: {audio_filename}")
                    st.caption(f" Total Processing Time (Extraction + Conversion): {extraction_time + conversion_time}s")

                    st.audio(audio_file_path, format="audio/mp3")
                    with open(audio_file_path, "rb") as f:
                        st.download_button(
                            f" Download {audio_filename}",
                            f,
                            file_name=audio_filename,
                            mime="audio/mp3",
                            key=f"download_{audio_filename}"
                        )

        st.subheader("Your Stored Audio Files")
        files = [f for f in os.listdir(user_dir) if f.endswith(".mp3")]
        if files:
            for i, file in enumerate(files):
                file_path = os.path.join(user_dir, file)
                st.audio(file_path, format="audio/mp3")
                col1, col2 = st.columns([3, 1])
                with col1:
                    with open(file_path, "rb") as f:
                        st.download_button(
                            f" Download {file}",
                            f,
                            file_name=file,
                            mime="audio/mp3",
                            key=f"stored_download_{i}"
                        )
                with col2:
                    if st.button(" Delete", key=f"delete_{i}"):
                        os.remove(file_path)
                        st.warning(f"{file} deleted!")
                        st.rerun()
        else:
            st.info("No files stored yet. Upload and convert to see them here.")

        if st.button("Sign Out"):
            del st.session_state["user"]
            del st.session_state["token"]
            st.session_state["page"] = "Login"
            st.success("Signed out successfully!")
            st.rerun()
    else:
        st.warning("Please log in to view the dashboard.")
