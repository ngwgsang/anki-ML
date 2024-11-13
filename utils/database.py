# utils/database.py

import os
import pandas as pd
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key are missing from environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Load flashcards from Supabase
def load_flashcards():
    try:
        data = supabase.table('flashcards').select('*').execute()
        flashcards = data.data if data.data else []
        today = pd.Timestamp.now()
        for card in flashcards:
            gold_time_raw = card.get('gold_time')
            card['gold_time'] = pd.to_datetime(gold_time_raw, errors='coerce') if gold_time_raw else pd.NaT
        
        # Sort flashcards by gold_time
        flashcards.sort(
            key=lambda x: (
                ((x['gold_time'] - today).days if pd.notna(x['gold_time']) and x['gold_time'] < today else float('inf')),
                (x['gold_time'] if pd.notna(x['gold_time']) and x['gold_time'] >= today else float('inf')),
                (-x['gold_time'].toordinal() if pd.notna(x['gold_time']) else 0)
            )
        )
        return flashcards
    except Exception as e:
        st.error(f"Error fetching flashcards from Supabase: {e}")
        return []

# Add a new flashcard to Supabase
def add_flashcard(word, meaning, example):
    try:
        supabase.table('flashcards').insert({
            "word": word,
            "meaning": meaning,
            "example": example,
            "gold_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }).execute()
    except Exception as e:
        st.error(f"Error adding flashcard: {e}")

# Update an existing flashcard's gold_time in Supabase
def update_gold_time(card_id, gold_time):
    try:
        supabase.table('flashcards').update({'gold_time': gold_time.strftime('%Y-%m-%d %H:%M:%S')}).eq('id', card_id).execute()
    except Exception as e:
        st.error(f"Error updating gold_time: {e}")

# Delete a flashcard from Supabase
def delete_flashcard(card_id):
    try:
        supabase.table('flashcards').delete().eq('id', card_id).execute()
        supabase.table('notes').delete().eq('flashcard_id', card_id).execute()  # Remove associated notes
    except Exception as e:
        st.error(f"Error deleting flashcard or notes: {e}")

# Update a flashcard from Supabase
def update_flashcard(card_id, new_word, new_meaning, new_example):
    try:
        supabase.table('flashcards').update({
            "word": new_word,
            "meaning": new_meaning,
            "example": new_example
        }).eq('id', card_id).execute()
    except Exception as e:
        st.error(f"Error deleting flashcard or notes: {e}")

# Load all notes
def load_all_notes():
    try:
        data = supabase.table('notes').select('*').execute()
        return data.data if data.data else []
    except Exception as e:
        st.error(f"Error fetching notes from Supabase: {e}")
        return []

# Load all notes associated with a flashcard
def load_notes(flashcard_id):
    try:
        data = supabase.table('notes').select('*').eq('flashcard_id', flashcard_id).execute()
        return data.data if data.data else []
    except Exception as e:
        st.error(f"Error fetching notes from Supabase: {e}")
        return []

# Add a note for a flashcard
def add_note(flashcard_id, title, content):
    try:
        supabase.table('notes').insert({
            "flashcard_id": flashcard_id,
            "title": title,
            "content": content
        }).execute()
    except Exception as e:
        st.error(f"Error adding note: {e}")

# Delete a note from Supabase
def delete_note(note_id):
    try:
        supabase.table('notes').delete().eq('id', note_id).execute()
    except Exception as e:
        st.error(f"Error deleting note: {e}")

def update_note(note_id, new_title, new_content):
    try:
        supabase.table('notes').update({
            "title": new_title,
            "content": new_content
        }).eq('id', note_id).execute()
    except Exception as e:
        st.error(f"Error updating note: {e}")
        

# Load study progress data
def load_study_progress():
    try:
        response = supabase.table('study_progress').select('*').order('date').execute()
        return pd.DataFrame(response.data if response.data else [])
    except Exception as e:
        st.error(f"Error fetching study progress data: {e}")
        return pd.DataFrame()

def update_study_progress(study_progress):
    today_str = datetime.now().strftime('%Y-%m-%d')
    try:
        # Check if there's already an entry for today
        response = supabase.table('study_progress').select('*').eq('date', today_str).execute()
        if response.data:
            # Update existing entry
            existing_progress = response.data[0]
            supabase.table('study_progress').update({
                "good_count": existing_progress["good_count"] + study_progress['good_count'],
                "normal_count": existing_progress["normal_count"] + study_progress['normal_count'],
                "bad_count": existing_progress["bad_count"] + study_progress['bad_count']
            }).eq('date', today_str).execute()
        else:
            # Insert new entry if no entry exists for today
            new_entry = {
                "date": today_str,
                "good_count": study_progress['good_count'],
                "normal_count": study_progress['normal_count'],
                "bad_count": study_progress['bad_count']
            }
            supabase.table('study_progress').insert(new_entry).execute()
    except Exception as e:
        print(f"Error updating study progress: {e}")