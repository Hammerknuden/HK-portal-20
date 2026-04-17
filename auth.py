import streamlit as st
import streamlit_authenticator as stauth
st.text('hello')


def login():
    names = ['Finn', 'Naja', 'Admin']
    usernames = ['finn', 'naja', 'admin']
    passwords = ['pc0012', 'pc0012nb', '0012']

    hashed_passwords = [stauth.Hasher().hash(passwords)
    print(hashed_passwords)]
    #hashed_passwords = [
    #'$2b$12$abc...',
    #'$2b$12$def...',
    #'$2b$12$ghi...'
    #]

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

    name, authentication_status, username = authenticator.login('Login', 'main')

    if authentication_status:
        authenticator.logout('Logout', 'sidebar')
        return True
    elif authentication_status is False:
        st.error("Forkert brugernavn eller password")
        return False
    else:
        st.warning("Indtast brugernavn og password")
        return None


def require_login():
    if not st.session_state.get("authentication_status"):
        st.warning("Log ind først")
        st.stop()


def require_admin():
    if st.session_state.get("username") != "admin":
        st.error("Kun admin har adgang til denne side")
        st.stop()

