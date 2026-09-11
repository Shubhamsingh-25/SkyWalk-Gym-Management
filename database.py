from config import supabase


def test_connection():
    response = supabase.table("gyms").select("id").limit(1).execute()
    return response


def get_gyms():
    response = supabase.table("gyms").select("*").execute()
    return response.data