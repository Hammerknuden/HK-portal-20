"""Dual-login transition UI; called on every protected portal page."""
import streamlit as st
from modules.auth_client import AuthClient, validate_config
from modules.auth_settings import auth_settings, access_token
from modules.password_recovery import render_recovery, render_forgot_password
from modules.user_invitation import render_invitation


def supabase_login():
    from portal_access import require_portal_user
    url = auth_settings(st.secrets)['SUPABASE_AUTH_URL']
    key = auth_settings(st.secrets)['SUPABASE_PUBLISHABLE_KEY']
    validate_config(url, key)
    client = AuthClient(url, key)
    render_invitation(st, client)
    render_recovery(client, [], [], role_check=client.portal_role)
    if not access_token(st.session_state):
        with st.form('portal_supabase_login', clear_on_submit=True):
            email = st.text_input('E-mail')
            password = st.text_input('Adgangskode', type='password')
            submitted = st.form_submit_button('Log ind')
        if submitted:
            token = None
            try:
                token = client.sign_in(email.strip(), password)['access_token']
                if not client.portal_role(token):
                    client.sign_out(token)
                    raise ValueError('Not approved')
            except Exception:
                st.error('Login kunne ikke gennemføres. Kontrollér adgang og loginoplysninger.')
            else:
                st.session_state.clear()
                st.session_state['portal_login_method'] = 'supabase'
                st.session_state['auth_access_token'] = token
                st.rerun()
        render_forgot_password(client)
        st.stop()
    require_portal_user()
    if st.sidebar.button('Log ud af Secure login'):
        token = access_token(st.session_state)
        try:
            client.sign_out(token)
        except Exception:
            pass
        st.session_state.clear()
        st.session_state['portal_login_method'] = 'supabase'
        st.rerun()
