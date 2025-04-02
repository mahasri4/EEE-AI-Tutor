import streamlit as st
import google.generativeai as genai
import openai
import pdfplumber
import docx
import speech_recognition as sr
from PIL import Image
import pytesseract
import sqlite3
from googleapiclient.discovery import build
from io import BytesIO
import requests
from pydub import AudioSegment
from pydub.playback import play

# API Configurations
genai.configure(api_key="AIzaSyAq49nklVKhcfImjtaGAQMbu6w_RvrARaw")
openai.api_key = "YOUR_OPENAI_API_KEY"
model_gemini = genai.GenerativeModel("gemini-pro")

def chat_with_gemini(prompt):
    response = model_gemini.generate_content(prompt)
    return response.text if response else "No response from Gemini AI."

def chat_with_openai(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": prompt}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except openai.error.OpenAIError as e:
        return f"Error: {e}"

# Database Setup
conn = sqlite3.connect("chatbot.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT
    )
""")
conn.commit()

def register_user(email, password):
    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        return True
    except:
        return False

def authenticate_user(email, password):
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    return cursor.fetchone() is not None

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def extract_text_from_word(word_file):
    doc = docx.Document(word_file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_image(image_file):
    image = Image.open(image_file)
    return pytesseract.image_to_string(image)

def extract_text_from_audio(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except:
            return "Could not process audio."

def get_pdf_from_drive(url):
    file_id = url.split("/d/")[1].split("/")[0]
    drive_url = f"https://drive.google.com/uc?id={file_id}"
    response = requests.get(drive_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        return None

def display_study_materials():
    cursor.execute("SELECT * FROM study_materials")
    materials = cursor.fetchall()
    for material in materials:
        st.markdown(f"**{material[1]}**")
        st.text_area("Extracted Content:", material[2], height=200)

def save_study_material(title, content):
    cursor.execute("INSERT INTO study_materials (title, content) VALUES (?, ?)", (title, content))
    conn.commit()

def play_audio(text):
    audio = AudioSegment.silent(duration=1000)
    play(audio)

def get_answer_for_student(question):
    cursor.execute("SELECT content FROM study_materials WHERE content LIKE ?", ('%' + question + '%',))
    result = cursor.fetchone()
    
    if result:
        return result[0]  # Return stored answer from study materials
    else:
        return chat_with_openai(question)  # Fetch from OpenAI if not found

# UI Setup
st.set_page_config(page_title="EEE AI Tutor", page_icon="⚡", layout="wide")
st.markdown(
    """
    <style>
        body {background-image: url("https://www.transparenttextures.com/patterns/asfalt-dark.png");}
        .title {text-align: center; font-size: 32px; font-weight: bold; color: #4CAF50;}
        .stButton button {width: 100%; border-radius: 10px; font-size: 16px;}
    </style>
    """, unsafe_allow_html=True
)

# Authentication
st.sidebar.title("🔑 Login / Register")
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if authenticate_user(email, password):
        st.session_state["logged_in"] = True
        st.session_state["email"] = email
    else:
        st.sidebar.warning("Invalid credentials. Please register.")

if st.sidebar.button("Register"):
    if register_user(email, password):
        st.sidebar.success("Registration successful. You can now log in.")
    else:
        st.sidebar.error("User already exists. Try logging in.")

if "logged_in" in st.session_state and st.session_state["logged_in"]:
    st.markdown("<p class='title'>⚡ AI Tutor for EEE Students ⚡</p>", unsafe_allow_html=True)
    
    if email == "mahasrielctriczone4@gmail.com":
        st.subheader("📂 Admin Panel - Upload Study Materials")
        admin_file = st.file_uploader("Upload PDF, Word, Image, or Audio", type=["pdf", "docx", "jpg", "png", "wav"])
        drive_url = st.text_input("Enter Google Drive PDF Link")
        if st.button("Upload & Extract"):
            if admin_file:
                extracted_text = ""
                if admin_file.type == "application/pdf":
                    extracted_text = extract_text_from_pdf(admin_file)
                elif admin_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    extracted_text = extract_text_from_word(admin_file)
                elif admin_file.type in ["image/jpeg", "image/png"]:
                    extracted_text = extract_text_from_image(admin_file)
                elif admin_file.type == "audio/wav":
                    extracted_text = extract_text_from_audio(admin_file)
                save_study_material(admin_file.name, extracted_text)
                st.success("Material saved.")
            elif drive_url:
                pdf_content = get_pdf_from_drive(drive_url)
                if pdf_content:
                    extracted_text = extract_text_from_pdf(pdf_content)
                    save_study_material("Drive PDF", extracted_text)
                    st.success("Material saved.")
    else:
        st.subheader("📚 Student Portal - Ask AI")
        question = st.text_input("Ask a question")
        if st.button("Get Answer"):
            response = get_answer_for_student(question)
            st.markdown(f"**Response:** {response}")
