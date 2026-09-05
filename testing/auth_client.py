"""Isolated Auth-only client. Never uses the portal's privileged database key."""
from urllib.parse import urlparse
from uuid import UUID

import requests


def validate_config(url, key, admin_ids):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/"):
        raise ValueError("SUPABASE_TEST_URL skal være projektets https-adresse.")
    if not key.startswith("sb_publishable_"):
        raise ValueError("Brug en sb_publishable_-nøgle til testlogin, ikke sb_secret_.")
    if not isinstance(admin_ids, (list, tuple)) or not admin_ids:
        raise ValueError("TEST_ADMIN_USER_IDS skal indeholde mindst ét User UID.")
    return frozenset(str(UUID(value)) for value in admin_ids)


def is_test_admin(user, admin_ids):
    # Never trust editable user_metadata for administrator permissions.
    return bool(user and user.get("id") in admin_ids)


class AuthClient:
    def __init__(self, url, key):
        self.url = url.rstrip("/") + "/auth/v1"
        self.key = key

    def _request(self, method, path, token=None, payload=None):
        headers = {"apikey": self.key}
        if token:
            headers["Authorization"] = "Bearer " + token
        response = requests.request(
            method, self.url + path, headers=headers, json=payload, timeout=15
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    def sign_in(self, email, password):
        return self._request("POST", "/token?grant_type=password", payload={
            "email": email, "password": password,
        })

    def get_user(self, token):
        return self._request("GET", "/user", token=token)

    def sign_out(self, token):
        return self._request("POST", "/logout?scope=local", token=token)
