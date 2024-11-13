import streamlit as st
from utils.database import supabase

def authenticate(username, password):
    response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
    if response.data:
        user = response.data[0]
        return user['id'], user['is_admin']
    else:
        return None, False

def check_login_status():
    if 'user_id' not in st.session_state:
        return False
    return True
