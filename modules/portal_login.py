"""Dual-login transition UI; called on every protected portal page."""
import streamlit as st
from testing.auth_client import AuthClient, resolve_role, validate_config


def choose_login(authenticator):
    current = st.session_state.get('portal_login_method', 'legacy')
    choice = st.sidebar.radio('Log ind med', ['legacy', 'supabase'],
        index=0 if current == 'legacy' else 1,
        format_func=lambda value: 'Nuværende login' if value == 'legacy' else 'Supabase',
        key='portal_login_choice')
    if choice != current:
        token = st.session_state.get('test_auth_access_token')
        if current == 'legacy' and st.session_state.get('authentication_status'):
            authenticator.logout(location='unrendered')
        if token:
            try:
                AuthClient(st.secrets['SUPABASE_TEST_URL'], st.secrets['SUPABASE_TEST_PUBLISHABLE_KEY']).sign_out(token)
            except Exception:
                pass
        st.session_state.clear()
        st.session_state['portal_login_method'] = choice
        st.rerun()
    st.session_state['portal_login_method'] = current


def supabase_login():
    from portal_access import require_test_user
    url = st.secrets['SUPABASE_TEST_URL']
    key = st.secrets['SUPABASE_TEST_PUBLISHABLE_KEY']
    admins = validate_config(url, key, st.secrets['TEST_ADMIN_USER_IDS'])
    users = st.secrets.get('TEST_USER_IDS', [])
    client = AuthClient(url, key)
    if not st.session_state.get('test_auth_access_token'):
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
                st.session_state['test_auth_access_token'] = token
                st.rerun()
        st.caption('Glemt adgangskode kan fortsat bruges i Supabase-testappen under overgangen.')
        st.stop()
    require_test_user()
    if st.sidebar.button('Log ud af Supabase'):
        token = st.session_state.get('test_auth_access_token')
        try:
            client.sign_out(token)
        except Exception:
            pass
        st.session_state.clear()
        st.session_state['portal_login_method'] = 'supabase'
        st.rerun()
