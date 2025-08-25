import streamlit as st
from db_config import get_connection, create_user_table
from gtts import gTTS
import os
import time
import docx
import fitz  

st.set_page_config(page_title="Text to Speech App", layout="wide")
create_user_table()

STORAGE_DIR = "user_files"
os.makedirs(STORAGE_DIR, exist_ok=True)

def signup(username, email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username,email,password) VALUES (%s,%s,%s)", (username,email,password))
    conn.commit()
    cursor.close()
    conn.close()
    st.success("Signup successful! Please log in.")
    st.session_state["page"] = "Login"


def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

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
    new_pass = st.text_input("Password", type="password", key="signup_pass") 

    if st.button("Sign Up"):
        if new_user and new_email and new_pass:
            signup(new_user, new_email, new_pass)
        else:
            st.warning("Please fill in all fields.")

    if st.button("Already have an account? Login"):
        st.session_state["page"] = "Login"
        st.rerun()

elif st.session_state["page"] == "Login":
    st.subheader("Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    
    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state["user"] = username
            st.session_state["page"] = "Dashboard"
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials.")

    if st.button("Don't have an account? Sign Up"):
        st.session_state["page"] = "Signup"
        st.rerun()

elif st.session_state["page"] == "Dashboard":
    if "user" in st.session_state:
        username = st.session_state["user"]
        st.subheader(f"Welcome, {username}")

        user_dir = os.path.join(STORAGE_DIR, username)
        os.makedirs(user_dir, exist_ok=True)

        uploaded_files = st.file_uploader("Upload text/PDF/DOCX files",type=["txt", "pdf", "docx"], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                text = extract_text(uploaded_file)
                if not text:
                    st.error(f" Could not read {uploaded_file.name}")
                    continue

                st.text_area(f"{uploaded_file.name}", text[:2000], height=150, key=f"text_{uploaded_file.name}")

                if st.button(f"Convert {uploaded_file.name}", key=f"convert_{uploaded_file.name}"):
                    timestamp = int(time.time())
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    audio_filename = f"{base_name}_{timestamp}.mp3"
                    audio_file_path = os.path.join(user_dir, audio_filename)

                    tts = gTTS(text=text, lang="en")
                    tts.save(audio_file_path)

                    st.success(f" File converted: {audio_filename}")
                    st.audio(audio_file_path, format="audio/mp3")
                    with open(audio_file_path, "rb") as f:
                        st.download_button(
                            f" Download {audio_filename}",
                            f,
                            file_name=audio_filename,
                            mime="audio/mp3",
                            key=f"download_{audio_filename}"
                        )
                        
        st.subheader(" Your Stored Audio Files")
        files = [f for f in os.listdir(user_dir) if f.endswith(".mp3")]
        if files:
            for i, file in enumerate(files):
                file_path = os.path.join(user_dir, file)
                st.audio(file_path, format="audio/mp3")
                with open(file_path, "rb") as f:
                    st.download_button(
                        f" Download {file}",
                        f, 
                        file_name=file,
                        mime="audio/mp3",
                        key=f"stored_download_{i}"
                    )
        else:
            st.info("No files stored yet. Upload and convert to see them here.")

        if st.button("Sign Out"):
            del st.session_state["user"]
            st.session_state["page"] = "Login"
            st.success("Signed out successfully!")
            st.rerun()
    else:
        st.warning("Please log in to view the dashbord.")
