import streamlit as st
from db_config import get_connection, create_user_table
import sqlite3
import bcrypt
import jwt 
import pyttsx3
import os
import time
import docx
import fitz
from gtts import gTTS
from datetime import datetime, timedelta
import math

# ---------------- Config ---------------- #
SECRET_KEY = "your_secret_key_here"
STORAGE_DIR = os.path.abspath("user_files")
os.makedirs(STORAGE_DIR, exist_ok=True)

# ---------------- Optional pydub ---------------- #
try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# ---------------- Database ---------------- #
def get_connection():
    return sqlite3.connect(DB_FILE)

def create_user_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_jwt_column():
    """Add jwt_token column if missing."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN jwt_token TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    conn.close()

# Run migrations
create_user_table()
add_jwt_column()

# ---------------- Auth ---------------- #
def signup(username, email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
    if cursor.fetchone():
        st.error("Username or email already exists")
        conn.close()
        return False

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed))
    conn.commit()
    conn.close()
    st.success("Signup successful! Please log in.")
    return True

def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()

    if user:
        stored_pass = user[3]
        if isinstance(stored_pass, str):
            stored_pass = stored_pass.encode("utf-8")

        if bcrypt.checkpw(password.encode(), stored_pass):
            token = jwt.encode(
                {"user_id": user[0], "username": username, "exp": datetime.utcnow() + timedelta(hours=2)},
                SECRET_KEY,
                algorithm="HS256"
            )
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            cursor.execute("UPDATE users SET jwt_token=%s WHERE id=%s", (token, user[0]))
            conn.commit()
            conn.close()
            return user, token

    conn.close()
    st.error("Invalid username or password")
    return None, None

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except jwt.ExpiredSignatureError:
        st.error("Token expired")
    except jwt.InvalidTokenError:
        st.error("Invalid token")
    return None

# ---------------- TTS ---------------- #
def init_tts_engine():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    if voices:
        engine.setProperty("voice", voices[0].id)
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 0.9)
    return engine

def text_to_wav_pyttsx3(text, username, user_dir):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{username}_{timestamp_str}.wav"
    filepath = os.path.join(user_dir, filename)
    engine = init_tts_engine()
    engine.save_to_file(text, filepath)
    engine.runAndWait()
    return filepath, timestamp_str

# ---------------- File Handling ---------------- #
def extract_text(uploaded_file):
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

# ---------------- Progress Simulation ---------------- #
def simulate_progress_bar(progress_bar, progress_text, estimated_time, step_text):
    progress_text.text(step_text)
    steps = 50
    sleep_time = estimated_time / steps
    for i in range(1, steps+1):
        progress_bar.progress(math.floor((i/steps)*100))
        time.sleep(sleep_time)

# ---------------- Streamlit UI ---------------- #
st.set_page_config(page_title="Text-to-Speech App", layout="wide")
st.title("📖 Text-to-Speech App")

if "page" not in st.session_state:
    st.session_state["page"] = "Signup"

# ---------------- Signup ---------------- #
if st.session_state["page"] == "Signup":
    st.subheader("Create Account")
    new_user = st.text_input("Username", key="signup_user")
    new_email = st.text_input("Email", key="signup_email")
    new_pass = st.text_input("Password", type="password", key="signup_pass")

    if st.button("Sign Up"):
        if new_user and new_email and new_pass:
            signup(new_user, new_email, new_pass)
    if st.button("Already have an account? Login"):
        st.session_state["page"] = "Login"
        st.rerun()

# ---------------- Login ---------------- #
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
            st.success(f"Welcome {username}!")
            st.rerun()

    st.divider()

    st.subheader("Login with JWT Token")
    jwt_token = st.text_input("JWT Token", key="login_token")
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

# ---------------- Dashboard ---------------- #
elif st.session_state["page"] == "Dashboard":
    if "user" in st.session_state:
        username = st.session_state["user"]
        token = st.session_state.get("token")
        st.subheader(f"Welcome, {username}")
        st.caption(f"JWT: {token}")

        user_dir = os.path.join(STORAGE_DIR, username)
        os.makedirs(user_dir, exist_ok=True)

        uploaded_files = st.file_uploader("Upload txt/pdf/docx", type=["txt", "pdf", "docx"], accept_multiple_files=True)
        if uploaded_files:
            for idx, uploaded_file in enumerate(uploaded_files):
                text = extract_text(uploaded_file)
                if not text:
                    st.error(f"Cannot read {uploaded_file.name}")
                    continue

                st.text_area(f"{uploaded_file.name}", text[:2000], height=150, key=f"text_{idx}")

                if st.button(f"Convert {uploaded_file.name}", key=f"convert_{idx}"):
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                    eta_text = st.empty()

                    text_len = len(text)
                    mp3_est_sec = max(2, text_len / 1000 * 2)
                    wav_est_sec = max(2, text_len / 1000 * 1)
                    pydub_est_sec = 1 if AudioSegment else 0

                    # Step 1: gTTS MP3
                    eta_text.text(f"⏳ Estimated time: {mp3_est_sec:.1f} minutes")
                    simulate_progress_bar(progress_bar, progress_text, mp3_est_sec, "Converting to MP3...")
                    mp3_path = os.path.join(user_dir, f"{username}_{int(time.time())}.mp3")
                    gTTS(text=text).save(mp3_path)

                    # Step 2: pyttsx3 WAV
                    eta_text.text(f"⏳ Estimated time: {wav_est_sec:.1f} minutes")
                    simulate_progress_bar(progress_bar, progress_text, wav_est_sec, "Converting to WAV...")
                    wav_path, timestamp_str = text_to_wav_pyttsx3(text, username, user_dir)

                    # Step 3: optional pydub WAV
                    wav_pydub_path = None
                    if AudioSegment:
                        eta_text.text(f"⏳ Estimated time: {pydub_est_sec:.1f} minutes")
                        simulate_progress_bar(progress_bar, progress_text, pydub_est_sec, "Converting MP3 to WAV with pydub...")
                        try:
                            audio = AudioSegment.from_mp3(mp3_path)
                            wav_pydub_path = os.path.join(user_dir, f"{username}_{int(time.time())}_pydub.wav")
                            audio.export(wav_pydub_path, format="wav")
                        except:
                            st.warning("pydub conversion failed")

                    progress_bar.progress(100)
                    progress_text.text(f"✅ Conversion completed at {timestamp_str}!")
                    eta_text.text("")

                    # Playback & download
                    st.audio(mp3_path)
                    with open(mp3_path, "rb") as f:
                        st.download_button("Download MP3", f, f"{uploaded_file.name}.mp3", "audio/mp3")

                    st.audio(wav_path)
                    with open(wav_path, "rb") as f:
                        st.download_button("Download WAV", f, f"{uploaded_file.name}.wav", "audio/wav")

                    if wav_pydub_path:
                        st.audio(wav_pydub_path)
                        with open(wav_pydub_path, "rb") as f:
                            st.download_button("Download WAV (pydub)", f, f"{uploaded_file.name}_pydub.wav", "audio/wav")

        # Stored files
        st.subheader("Stored Audio Files")
        files = [f for f in os.listdir(user_dir) if f.endswith((".mp3", ".wav"))]
        for i, file in enumerate(sorted(files)):
            file_path = os.path.join(user_dir, file)
            st.write(f"**{file}**")
            st.audio(file_path)
            with open(file_path, "rb") as f:
                st.download_button(f"Download {file}", f, file, "audio/mp3" if file.endswith(".mp3") else "audio/wav")
            if st.button(f"Delete {file}", key=f"del_{i}"):
                os.remove(file_path)
                st.warning(f"{file} deleted")
                st.rerun()

        if st.button("Sign Out"):
            del st.session_state["user"]
            del st.session_state["token"]
            st.session_state["page"] = "Login"
            st.success("Signed out")
            st.rerun()
    else:
        st.warning("Please log in to access the dashboard.")
