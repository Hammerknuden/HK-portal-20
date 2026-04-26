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
    'hk_portal',
    'hammerknuden',
    cookie_expiry_days=30
)


def require_login():
    authenticator.login(location='main')

    authentication_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username")

    if authentication_status:
        authenticator.logout('Logout', 'sidebar')
        return True

    if authentication_status is False:
        st.error("Forkert brugernavn eller kode")
        st.stop()

    st.info("Indtast brugernavn og kode")
    st.stop()


def require_admin():
    if st.session_state.get("username") != "admin":
        st.error("Kun admin har adgang til denne side")
        st.stop()

