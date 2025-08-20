import streamlit as st
from db_config import get_connection, create_user_table
import os

st.set_page_config(page_title="Text to Speech App", layout="wide")
create_user_table()

def signup(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
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

if "page" not in st.session_state:
    st.session_state["page"] = "Signup"   

st.title("🗣️ Text-to-Speech App")

if st.session_state["page"] == "Signup":
    st.subheader("Create Account")
    new_user = st.text_input("Username", key="signup_user")
    new_pass = st.text_input("Password", type="password", key="signup_pass")
    if st.button("Sign Up"):
        if new_user and new_pass:
            signup(new_user, new_pass)
        else:
            st.warning("Please fill in both fields.")

elif st.session_state["page"] == "Login":
    st.subheader("Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state["user"] = username
            st.session_state["page"] = "Dashboard"   # redirect to dashboard
            st.success(f"Welcome, {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials.")

elif st.session_state["page"] == "Dashboard":
    if "user" in st.session_state:
        st.subheader(f"Welcome, {st.session_state['user']} 👋")
        
        uploaded_file = st.file_uploader("Upload a text file", type=["txt"])
        if uploaded_file is not None:
            text = uploaded_file.read().decode("utf-8")
            st.text_area("File Content", text, height=200)

            if st.button("Convert to Audio"):
                audio_url = f"https://api.streamelements.com/kappa/v2/speech?voice=Brian&text={text}"
                st.audio(audio_url, format="audio/mp3")
                st.markdown(f"[⬇️ Download Audio]({audio_url})", unsafe_allow_html=True)

        if st.button("Sign Out"):
            del st.session_state["user"]
            st.session_state["page"] = "Login"
            st.success("Signed out successfully!")
            st.rerun()
    else:
        st.warning("Please log in to view the dashboard.")
