import streamlit as st
from supabase import create_client, Client


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


supabase = get_supabase_client()