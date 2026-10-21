"""Read configured portal accounts; roles come from portal configuration."""
from uuid import UUID

from modules.auth_settings import auth_settings


def configured_roles(secrets):
    settings = auth_settings(secrets)
    roles = {}
    for setting, role in (("USER_IDS", "Almindelig bruger"), ("ADMIN_USER_IDS", "Administrator")):
        values = settings[setting]
        if not isinstance(values, (list, tuple)):
            raise ValueError("User IDs must be lists")
        for value in values:
            roles[str(UUID(value))] = role
    return roles


def read_directory(secrets, client_factory):
    """Call only after require_admin; never expose the service client to pages."""
    settings = auth_settings(secrets)
    url = str(secrets.get("SUPABASE_URL", "")).rstrip("/")
    if not url or url != str(settings["SUPABASE_AUTH_URL"]).rstrip("/"):
        raise ValueError("Authentication and server projects must match")
    key = secrets.get("SUPABASE_KEY", "")
    if not key:
        raise ValueError("Server key missing")
    roles = configured_roles(secrets)
    client = client_factory(url, key)
    rows = []
    for uid, role in roles.items():
        user = client.auth.admin.get_user_by_id(uid).user
        if user is None or str(user.id) != uid:
            raise ValueError("Configured account not found")
        metadata = user.user_metadata or {}
        name = next((metadata[field].strip() for field in ("display_name", "full_name", "name")
                     if isinstance(metadata.get(field), str) and metadata[field].strip()), "Navn mangler")
        rows.append({"Navn": name, "E-mail": user.email or "", "Rolle": role})
    return sorted(rows, key=lambda row: (row["Navn"].casefold(), row["E-mail"].casefold()))


def load_user_directory():
    import streamlit as st
    from auth import require_admin
    from portal_access import is_restore_test

    require_admin()
    if is_restore_test():
        raise ValueError("Directory is not enabled in restore testing")
    from supabase import create_client, ClientOptions

    # A separate server client, never cached or shared with user-token clients.
    return read_directory(st.secrets, lambda url, key: create_client(
        url, key, options=ClientOptions(persist_session=False, auto_refresh_token=False)))
