"""Isolated test client. Never uses the portal's privileged database key."""
from urllib.parse import urlparse
from uuid import UUID

import requests

TEST_TABLES = ("hk_dtb", "historie_new", "bookin_pace", "high_season", "breakfast_notes", "Events")


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


def resolve_role(user, admin_ids, user_ids):
    if is_test_admin(user, admin_ids):
        return "admin"
    if user and user.get("id") in user_ids:
        return "user"
    return None


class AuthClient:
    def __init__(self, url, key):
        self.rest_url = url.rstrip("/") + "/rest/v1"
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

    def probe_table(self, table, token):
        """Read at most one visible row; never return guest data or raw errors."""
        if table not in TEST_TABLES or not token:
            raise ValueError("Vælg en kendt tabel og log ind først.")
        try:
            response = requests.request(
                "GET", self.rest_url + "/" + table,
                headers={"apikey": self.key, "Authorization": "Bearer " + token,
                         "Accept-Profile": "public"},
                params={"select": "*", "limit": "1"}, timeout=15,
            )
            status = response.status_code
            if status == 200:
                rows = response.json()
                if not isinstance(rows, list):
                    return {"Tabel": table, "HTTP": status, "Resultat": "Uventet svar"}
                message = ("Læseadgang bekræftet: mindst én synlig række" if rows else
                           "Ingen synlige rækker: tabellen kan være tom eller filtreret af RLS")
            elif status in (401, 403):
                message = "Adgang afvist eller session ugyldig"
            elif status == 404:
                message = "Tabel ikke fundet eller ikke tilgængelig via API"
            else:
                message = "Forespørgslen fejlede; adgang er ikke afklaret"
            return {"Tabel": table, "HTTP": status, "Resultat": message}
        except (requests.RequestException, ValueError):
            return {"Tabel": table, "HTTP": "–", "Resultat": "Forbindelsesfejl eller ugyldigt svar; prøv igen"}
