"""Production settings with explicit fallback for existing deployments.

Never fall back from an explicitly configured empty value or to a service key.
"""

def auth_settings(secrets):
    aliases = {
        "SUPABASE_AUTH_URL": "SUPABASE_TEST_URL",
        "SUPABASE_PUBLISHABLE_KEY": "SUPABASE_TEST_PUBLISHABLE_KEY",
        "ADMIN_USER_IDS": "TEST_ADMIN_USER_IDS",
        "USER_IDS": "TEST_USER_IDS",
    }
    return {name: secrets[name] if name in secrets else secrets.get(old, [] if name.endswith("IDS") else "")
            for name, old in aliases.items()}


def access_token(session):
    """Allow existing sessions and the diagnostic app during the transition."""
    return session.get("auth_access_token", session.get("test_auth_access_token"))
