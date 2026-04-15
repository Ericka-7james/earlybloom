from __future__ import annotations

from supabase import Client, create_client

from app.core.auth_settings import auth_settings

auth_settings.validate()

_public_client: Client | None = None
_service_client: Client | None = None


def get_supabase_public_client() -> Client:
    """Returns a Supabase client for user-facing auth flows."""
    global _public_client

    print("SUPABASE_URL:", repr(auth_settings.supabase_url))
    print("HAS_PUBLISHABLE:", bool(auth_settings.supabase_publishable_key))
    print("HAS_SECRET:", bool(auth_settings.supabase_secret_key))

    if _public_client is None:
        _public_client = create_client(
            auth_settings.supabase_url,
            auth_settings.supabase_publishable_key,
        )

    return _public_client


def get_supabase_service_client() -> Client:
    """Returns a Supabase client for trusted server-side access."""
    global _service_client

    if _service_client is None:
        _service_client = create_client(
            auth_settings.supabase_url,
            auth_settings.supabase_secret_key,
        )

    return _service_client