"""Separate Streamlit entrypoint: no import of production auth or pages."""
import sys
import runpy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import streamlit as st
from testing.auth_client import AuthClient, TEST_TABLES, resolve_role, validate_config

st.set_page_config(page_title="HK – logintest", page_icon="🧪")
st.title("HK – testmiljø")
st.caption("Test af Supabase-login og læseadgang til databasen.")

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

user_ids = st.secrets.get("TEST_USER_IDS", [])
client = AuthClient(url, key)
token_key = "test_auth_access_token"
context = (url, key, tuple(sorted(admin_ids)), tuple(sorted(user_ids)))
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
                if resolve_role(user, admin_ids, user_ids):
                    st.session_state.clear()
                    st.session_state["test_auth_context"] = context
                    st.session_state[token_key] = token
                    st.rerun()
                else:
                    try:
                        client.sign_out(token)
                    except Exception:
                        pass
                    st.error("Brugeren har ikke adgang til testappen.")
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

role = resolve_role(user, admin_ids, user_ids)
if not role:
    st.session_state.pop(token_key, None)
    st.error("Ingen adgang til testappen.")
    st.stop()

st.success("Login bekræftet – " + ("testadministrator" if role == "admin" else "almindelig testbruger"))
st.write("E-mail:", user.get("email", ""))
st.write("User UID:", user["id"])
st.info("Rollen gælder kun denne testapp. Databasens adgangspolitikker er ikke ændret.")
if st.sidebar.button("Log ud"):
    for session_key in list(st.session_state):
        if session_key != token_key:
            del st.session_state[session_key]
    token = st.session_state.pop(token_key)
    try:
        client.sign_out(token)
    except Exception:
        st.warning("Du er logget ud lokalt, men serverens session kunne ikke afsluttes.")
        st.stop()
    st.rerun()

st.sidebar.caption("TESTMILJØ · Læsetilstand")
pages = {
    "Adgangstest": None,
    "Booking": "1_Booking.py",
    "Databaseopslag": "2_databaseopslag.py",
    "In and Out": "3_In and Out.py",
    "Links": "4_Links.py",
    "Breakfast": "5_breakfast.py",
    "Timeline": "6_timeline.py",
    "Statistik": "8_statestik.py",
}
if role == "admin":
    pages.update({"Setup": "7_setup.py", "Booking.com-afstemning": "9_Booking_com_kontrol.py"})
selected_page = st.sidebar.selectbox("Side", list(pages))
if pages[selected_page]:
    st.info("Testmiljøet er i læsetilstand. Lagring, sletning og mailafsendelse er ikke aktiveret.")
    try:
        runpy.run_path(str(ROOT / "pages" / pages[selected_page]), run_name="__test_page__")
    except Exception:
        st.error("Siden kunne ikke gennemføres. Kontrollér læseadgang på Adgangstest. Skrivehandlinger er blokeret i testmiljøet.")
    st.stop()

st.subheader("Test databaseadgang")
st.caption("Tester public-tabeller med din indloggede bruger. Ingen data ændres.")
st.write("Supabase-projekt:", url)
selected_tables = st.multiselect("Tabeller", TEST_TABLES, default=list(TEST_TABLES))
if st.button("Test læseadgang", disabled=not selected_tables):
    with st.spinner("Kontrollerer adgang …"):
        results = [client.probe_table(table, st.session_state[token_key])
                   for table in selected_tables]
    st.dataframe(results, hide_index=True, use_container_width=True)
    st.info(
        "Ingen synlige rækker er ikke bevis for manglende adgang: tabellen kan være tom, "
        "eller RLS kan skjule rækkerne. En synlig række bekræfter kun læseadgang til "
        "mindst én række, ikke alle rækker eller adgang til at skrive og slette."
    )
    st.caption("Der hentes højst én række pr. tabel. Gæsteoplysninger vises ikke.")
