import streamlit as st
from gtts import gTTS
from io import BytesIO

# Function to generate and play audio
def generate_audio(text, lang='ja'):
    audio_data = BytesIO()
    tts = gTTS(text=text, lang=lang)
    tts.write_to_fp(audio_data)
    audio_data.seek(0)  # Reset file pointer to the beginning
    return audio_data