"""Separate Streamlit entrypoint: no import of production auth or pages."""
import streamlit as st
from auth_client import AuthClient, is_test_admin, validate_config

st.set_page_config(page_title="HK – logintest", page_icon="🧪")
st.title("HK – testmiljø")
st.caption("Test af Supabase-login. Bookingdata og dokumenter er ikke tilkoblet.")

try:
    if st.secrets.get("APP_ENV") != "test":
        raise ValueError('Testappen kræver APP_ENV = "test".')
    if st.secrets.get("AUTH_MODE") != "supabase":
        raise ValueError('Testappen kræver AUTH_MODE = "supabase".')
    url = st.secrets["SUPABASE_TEST_URL"]
    key = st.secrets["SUPABASE_TEST_PUBLISHABLE_KEY"]
    admin_ids = validate_config(url, key, st.secrets["TEST_ADMIN_USER_IDS"])
except (KeyError, ValueError, FileNotFoundError):
    st.info("Udfyld testappens Secrets efter testing/secrets.example.toml.")
    st.stop()

client = AuthClient(url, key)
token_key = "test_auth_access_token"
context = (url, key, tuple(sorted(admin_ids)))
if st.session_state.get("test_auth_context") != context:
    st.session_state.pop(token_key, None)
    st.session_state["test_auth_context"] = context

if token_key not in st.session_state:
    with st.form("test_login", clear_on_submit=True):
        email = st.text_input("E-mail")
        password = st.text_input("Adgangskode", type="password")
        submitted = st.form_submit_button("Log ind")
    if submitted:
        if not email.strip() or not password:
            st.error("Indtast e-mail og adgangskode.")
        else:
            try:
                result = client.sign_in(email.strip(), password)
                token = result["access_token"]
                user = client.get_user(token)
                if is_test_admin(user, admin_ids):
                    st.session_state[token_key] = token
                    st.rerun()
                else:
                    try:
                        client.sign_out(token)
                    except Exception:
                        pass
                    st.error("Brugeren har ikke administratoradgang til testappen.")
            except Exception:
                st.error("Login kunne ikke gennemføres. Kontrollér oplysningerne og forbindelsen.")
    st.stop()

try:
    user = client.get_user(st.session_state[token_key])
except Exception:
    st.session_state.pop(token_key, None)
    st.warning("Sessionen kunne ikke bekræftes. Log ind igen.")
    st.button("Til login", on_click=lambda: None)
    st.stop()

if not is_test_admin(user, admin_ids):
    st.session_state.pop(token_key, None)
    st.error("Ingen administratoradgang til testappen.")
    st.stop()

st.success("Login bekræftet – du er testadministrator.")
st.write("E-mail:", user.get("email", ""))
st.write("User UID:", user["id"])
st.info("Rollen gælder kun denne testapp. Databasens adgangspolitikker er ikke ændret.")
if st.button("Log ud"):
    token = st.session_state.pop(token_key)
    try:
        client.sign_out(token)
    except Exception:
        st.warning("Du er logget ud lokalt, men serverens session kunne ikke afsluttes.")
        st.stop()
    st.rerun()
