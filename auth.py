import streamlit as st
import streamlit_authenticator as stauth

names = ['Finn', 'Naja', 'Admin']
usernames = ['finn', 'naja', 'admin']
passwords = ['pc0012', 'pc0012nb', '0012']
ADMIN_USERNAMES = {"admin", "finn"}

hashed_passwords = [stauth.Hasher().hash(pw) for pw in passwords]

credentials = {
    "usernames": {
        usernames[i]: {
            "name": names[i],
            "password": hashed_passwords[i]
        }
        for i in range(len(usernames))
    }
}

authenticator = stauth.Authenticate(
    credentials,
    'hk_portal2',
    'hammerknudenportal',
    cookie_expiry_days=30
)


def require_login():

    defaults = {
        "authentication_status": None,
        "name": None,
        "username": None,
        "logout": False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    authenticator.login(location="main")

    status = st.session_state.get("authentication_status")

    if status is None:
        st.info("Indtast brugernavn og kode")
        st.stop()

    if status is False:
        st.error("Forkert login")
        st.stop()

    authenticator.logout("Logout", "sidebar")
#def require_login():
#    authenticator.login(location="main")

#    status = st.session_state.get("authentication_status")

#    if status is None:
#        st.info("Indtast brugernavn og kode")
#        st.stop()

#    if status is False:
#        st.error("Forkert login")
#        st.stop()

#    authenticator.logout('Logout', 'sidebar')


def require_admin():
    if not st.session_state.get("authentication_status"):
        st.error("Ikke logget ind")
        st.stop()

    username = str(st.session_state.get("username") or "").lower()
    if username not in ADMIN_USERNAMES:
        st.error("Kun admin har adgang til denne side")
        st.stop()


