import streamlit as st
import streamlit_authenticator as stauth

names = ['Finn', 'Naja', 'Admin']
usernames = ['finn', 'naja', 'admin']
passwords = ['pc0012', 'pc0012nb', '0012']

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
    authenticator.login(location="main")

    status = st.session_state.get("authentication_status")

    if status is None:
        st.info("Indtast brugernavn og kode")
        return False

    if status is False:
        st.error("Forkert brugernavn eller kode")
        return False

    authenticator.logout('Logout', 'sidebar')
    return True


def require_admin():
    if not st.session_state.get("authentication_status"):
        st.error("Ikke logget ind")
        st.stop()

    if st.session_state.get("username") != "admin":
        st.error("Kun admin har adgang til denne side")
        st.stop()

