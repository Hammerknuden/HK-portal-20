"""Dual-login transition UI; called on every protected portal page."""
import streamlit as st
from modules.auth_client import AuthClient, resolve_role, validate_config
from modules.auth_settings import auth_settings, access_token
from modules.password_recovery import render_recovery, render_forgot_password


def choose_login(authenticator):
    if st.query_params.get("token_hash") or any(
            name in st.session_state for name in ("recovery_hash", "recovery_access", "recovery_invalid", "recovery_success")):
        supabase_login()
        return
    current = st.session_state.get('portal_login_method', 'supabase')
    choice = st.sidebar.radio('Log ind med', ['supabase', 'legacy'],
        index=0 if current == 'supabase' else 1,
        format_func=lambda value: 'Legacy login (reserve)' if value == 'legacy' else 'Secure login',
        key='portal_login_choice')
    if choice != current:
        token = access_token(st.session_state)
        if current == 'legacy' and st.session_state.get('authentication_status'):
            authenticator.logout(location='unrendered')
        if token:
            try:
                AuthClient(auth_settings(st.secrets)['SUPABASE_AUTH_URL'], auth_settings(st.secrets)['SUPABASE_PUBLISHABLE_KEY']).sign_out(token)
            except Exception:
                pass
        st.session_state.clear()
        st.session_state['portal_login_method'] = choice
        st.rerun()
    st.session_state['portal_login_method'] = current


def supabase_login():
    from portal_access import require_portal_user
    url = auth_settings(st.secrets)['SUPABASE_AUTH_URL']
    key = auth_settings(st.secrets)['SUPABASE_PUBLISHABLE_KEY']
    admins = validate_config(url, key, auth_settings(st.secrets)['ADMIN_USER_IDS'])
    users = auth_settings(st.secrets)['USER_IDS']
    client = AuthClient(url, key)
    render_recovery(client, admins, users)
    if not access_token(st.session_state):
        with st.form('portal_supabase_login', clear_on_submit=True):
            email = st.text_input('E-mail')
            password = st.text_input('Adgangskode', type='password')
            submitted = st.form_submit_button('Log ind')
        if submitted:
            token = None
            try:
                token = client.sign_in(email.strip(), password)['access_token']
                if not resolve_role(client.get_user(token), admins, users):
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
