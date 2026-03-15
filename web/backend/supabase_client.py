"""
Supabase client initialization and authentication helpers.
"""

import os

import jwt
from supabase import Client, create_client


def get_supabase() -> Client:
    """Return an initialized Supabase client.

    Reads SUPABASE_URL and SUPABASE_KEY from environment variables.
    """
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def get_user_from_token(token: str) -> dict:
    """Verify a Supabase JWT and return the user payload.

    Args:
        token: The Bearer token from the Authorization header.

    Returns:
        A dict with at least ``sub`` (user ID) and ``email``.

    Raises:
        ValueError: If the token is invalid or expired.
    """
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if not jwt_secret:
        # Fallback: use Supabase client to verify
        supabase = get_supabase()
        user_response = supabase.auth.get_user(token)
        if user_response is None or user_response.user is None:
            raise ValueError("Invalid or expired token")
        user = user_response.user
        return {
            "sub": user.id,
            "email": user.email,
        }

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
    }
