import streamlit as st
import streamlit_authenticator as stauth

names = ['Finn', 'Naja', 'Admin']
usernames = ['finn', 'naja', 'admin']
passwords = ['pc0012', 'pc0012nb', '0012']

hashed_passwords = [stauth.Hasher().hash(pw) for pw in passwords]
#hashed_passwords = stauth.Hasher().generate(passwords)
#hashed_passwords = stauth.Hasher(passwords).generate()
#hashed_passwords = stauth.Hasher.hash_passwords(passwords)
print(hashed_passwords)

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
    name, authentication_status, username = authenticator.login(location='main')

    if authentication_status:
        authenticator.logout('Logout', 'sidebar')
        return True

    elif authentication_status is False:
        st.error("Forkert brugernavn eller kode")
        st.stop()

    else:
        st.info("Indtast brugernavn og kode")
        st.stop()


def require_admin():
    if st.session_state.get("username") != "admin":
        st.error("Kun admin har adgang til denne side")
        st.stop()

