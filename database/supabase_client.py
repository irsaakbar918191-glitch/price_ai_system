import os
from typing import Any, Dict, Optional

from supabase import Client, create_client

from config import Config


class SupabaseClient:
    _client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured.")
            cls._client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        return cls._client

    @classmethod
    def get_service_client(cls) -> Client:
        if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY must be configured.")
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)

    @staticmethod
    def get_auth_header(token: Optional[str]) -> Dict[str, str]:
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def get_user_from_token(token: str):
        client = SupabaseClient.get_client()
        try:
            user = client.auth.get_user(token)
            return user
        except Exception:
            return None
