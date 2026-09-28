from supabase import create_client, Client
from config import Config

def get_supabase() -> Client:
    url = Config.SUPABASE_URL
    key = Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_KEY
    if not url or not key:
        raise ValueError("SUPABASE_URL ya SUPABASE_KEY missing hai")
    return create_client(url, key)

def get_public_supabase() -> Client:
    url = Config.SUPABASE_URL
    key = Config.SUPABASE_KEY
    if not url or not key:
        raise ValueError("SUPABASE_KEY missing hai")
    return create_client(url, key)