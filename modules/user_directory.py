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


def directory_client(secrets, client_factory):
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
    return client, roles


def read_directory(secrets, client_factory, include_ids=False):
    client, roles = directory_client(secrets, client_factory)
    rows = []
    for uid, role in roles.items():
        user = client.auth.admin.get_user_by_id(uid).user
        if user is None or str(user.id) != uid:
            raise ValueError("Configured account not found")
        metadata = user.user_metadata or {}
        name = next((metadata[field].strip() for field in ("display_name", "full_name", "name")
                     if isinstance(metadata.get(field), str) and metadata[field].strip()), "Navn mangler")
        row = {"Navn": name, "E-mail": user.email or "", "Rolle": role}
        if include_ids:
            row["uid"] = uid
        rows.append(row)
    return sorted(rows, key=lambda row: (row["Navn"].casefold(), row["E-mail"].casefold()))


def load_user_directory(include_ids=False):
    import streamlit as st
    from auth import require_admin
    from portal_access import is_restore_test

    require_admin()
    if is_restore_test():
        raise ValueError("Directory is not enabled in restore testing")
    from supabase import create_client, ClientOptions

    # A separate server client, never cached or shared with user-token clients.
    return read_directory(st.secrets, lambda url, key: create_client(
        url, key, options=ClientOptions(persist_session=False, auto_refresh_token=False)), include_ids=include_ids)


def update_display_name(secrets, client_factory, uid, name):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("Navnet skal være mellem 1 og 100 tegn.")
    name = name.strip()
    uid = str(UUID(uid))
    if uid not in configured_roles(secrets):
        raise ValueError("Brugeren har ikke adgang til portalen.")
    client, _ = directory_client(secrets, client_factory)
    user = client.auth.admin.get_user_by_id(uid).user
    if user is None or str(user.id) != uid:
        raise ValueError("Brugeren kunne ikke findes.")
    metadata = dict(user.user_metadata or {})
    metadata["display_name"] = name
    client.auth.admin.update_user_by_id(uid, {"user_metadata": metadata})
    saved = client.auth.admin.get_user_by_id(uid).user
    if saved is None or str(saved.id) != uid or (saved.user_metadata or {}).get("display_name") != name:
        raise ValueError("Navneændringen kunne ikke bekræftes.")
    return name


def save_user_display_name(uid, name):
    import streamlit as st
    from auth import require_admin
    from portal_access import is_restore_test
    require_admin()
    if is_restore_test():
        raise ValueError("User administration is disabled in restore testing")
    from supabase import create_client, ClientOptions
    return update_display_name(st.secrets, lambda url, key: create_client(
        url, key, options=ClientOptions(persist_session=False, auto_refresh_token=False)), uid, name)
