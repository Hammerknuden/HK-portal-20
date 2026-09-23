"""A bounded Auth/RLS test against one synthetic hk_dtb booking."""
import requests

TEST_SEASON = 2099
TEST_BOOKING = 99999
TEST_NAME = "AUTH WRITE TEST - NOT A GUEST"


def is_booking_300_patch(method, path, params, payload):
    """Only the ordinary edit form for the agreed October test booking."""
    from datetime import date
    fields = {"booking_number", "familie_navn", "email", "telefon", "checkin_date",
              "checkout_date", "nation", "web", "ankomst", "bed", "morgenmad",
              "room_number", "season"}
    required = {"season": ["eq.2026"], "booking_number": ["eq.300"], "navn": ["eq.NN"]}
    if (method != "PATCH" or path != "/rest/v1/hk_dtb"
            or not isinstance(payload, dict) or set(payload) != fields
            or any(params.get(k) != v for k, v in required.items())
            or not set(params).issubset({*required, "id", "select"})):
        return False
    ids = params.get("id", [])
    if len(ids) != 1 or not ids[0].startswith("eq.") or not ids[0][3:].isdigit():
        return False
    try:
        return (str(payload["season"]) == "2026" and str(payload["booking_number"]) == "300"
                and date(2026, 10, 1) <= date.fromisoformat(payload["checkin_date"])
                < date.fromisoformat(payload["checkout_date"]) <= date(2026, 11, 1))
    except (ValueError, TypeError):
        return False


def is_scoped_comment_patch(method, path, params, payload):
    """Allow only a comment PATCH targeting the reserved booking and one row ID."""
    if method != "PATCH" or path != "/rest/v1/hk_dtb" or not isinstance(payload, dict):
        return False
    if set(payload) != {"comments"}:
        return False
    comment = payload["comments"]
    if not isinstance(comment, str) or not comment.strip() or len(comment) > 500:
        return False
    required = {"season": "eq.2099", "booking_number": "eq.99999",
                "navn": "eq." + TEST_NAME, "web": "eq.cansl"}
    if any(params.get(key) != [value] for key, value in required.items()):
        return False
    row_id = params.get("id", [])
    if len(row_id) != 1 or not row_id[0].startswith("eq.") or not row_id[0][3:].isdigit():
        return False
    return set(params).issubset({*required, "id", "comments", "select"})


def save_booking_test_comment(client, row_id, previous_comment, comment):
    if not isinstance(comment, str) or not comment.strip() or len(comment) > 500:
        raise ValueError("Brug 1–500 tegn.")
    def scope(query):
        return (query.eq("id", int(row_id)).eq("season", TEST_SEASON)
                .eq("booking_number", TEST_BOOKING).eq("navn", TEST_NAME).eq("web", "cansl"))
    query = scope(client.table("hk_dtb").update({"comments": comment}))
    query = query.is_("comments", "null") if previous_comment is None else query.eq("comments", previous_comment)
    result = query.execute()
    if not result.data or len(result.data) != 1:
        raise ValueError("Ingen ændring bekræftet. Genindlæs booking og kontrollér rettigheder.")
    verified = scope(client.table("hk_dtb").select("id,comments")).execute()
    if len(verified.data or []) != 1 or verified.data[0].get("comments") != comment:
        raise ValueError("Ændringen kunne ikke genlæses.")


class BookingWriteProbe:
    def __init__(self, auth_client, token, admin_ids):
        self.auth = auth_client
        self.token = token
        self.admin_ids = frozenset(admin_ids)

    def _authorize(self):
        user = self.auth.get_user(self.token)
        if not user or user.get("id") not in self.admin_ids:
            raise PermissionError("Skrivetesten er kun til administratorer.")

    def _call(self, method, params=None, payload=None):
        self._authorize()
        if method not in ("GET", "POST", "PATCH"):
            raise ValueError("Handlingen er ikke understøttet.")
        response = requests.request(
            method, self.auth.rest_url + "/hk_dtb",
            headers={"apikey": self.auth.key, "Authorization": "Bearer " + self.token,
                     "Accept-Profile": "public", "Content-Profile": "public",
                     "Prefer": "return=representation"},
            params=params, json=payload, timeout=15,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("Uventet svar fra databasen.")
        return rows

    @staticmethod
    def _scope():
        return {"season": f"eq.{TEST_SEASON}", "booking_number": f"eq.{TEST_BOOKING}"}

    def read(self):
        rows = self._call("GET", {**self._scope(), "select": "id,navn,web,comments", "limit": "2"})
        if len(rows) > 1 or any(r.get("navn") != TEST_NAME or r.get("web") != "cansl" for r in rows):
            raise ValueError("Testnummeret er optaget eller ændret. Ingen skrivning udført.")
        return rows[0] if rows else None

    def create(self):
        if self.read() is not None:
            raise ValueError("Testbookingen findes allerede. Brug ændringstesten.")
        payload = {
            "season": TEST_SEASON, "booking_number": TEST_BOOKING, "navn": TEST_NAME,
            "checkin_date": "2099-01-01", "checkout_date": "2099-01-02",
            "booking_date": "2099-01-01", "web": "cansl", "room_number": 7,
            "numb_rooms": 1, "numb_guests": 0, "pris": "0", "movable": False,
            "comments": "Supabase Auth: oprettelsestest",
        }
        rows = self._call("POST", {"select": "id"}, payload)
        current = self.read()
        if len(rows) != 1 or not current or current["id"] != rows[0]["id"]:
            raise ValueError("Skrivning kunne ikke bekræftes. Genindlæs før næste forsøg.")
        return current

    def update_comment(self, row_id, previous_comment, new_comment):
        if not isinstance(new_comment, str) or not new_comment.strip() or len(new_comment) > 500:
            raise ValueError("Kommentaren skal indeholde 1–500 tegn.")
        current = self.read()
        if not current or current["id"] != row_id or current.get("comments") != previous_comment:
            raise ValueError("Rækken er ændret siden visningen. Genindlæs først.")
        params = {**self._scope(), "id": f"eq.{row_id}", "navn": f"eq.{TEST_NAME}",
                  "web": "eq.cansl", "select": "id,comments",
                  "comments": "is.null" if previous_comment is None else "eq." + previous_comment}
        rows = self._call("PATCH", params, {"comments": new_comment})
        if len(rows) != 1 or rows[0].get("comments") != new_comment:
            raise ValueError("Ingen ændring bekræftet. RLS kan have afvist den, eller rækken er ændret.")
        verified = self.read()
        if not verified or verified["id"] != row_id or verified.get("comments") != new_comment:
            raise ValueError("Ændringen kunne ikke genlæses. Genindlæs før næste forsøg.")
        return verified


def render_write_probe(auth_client, token, admin_ids):
    import streamlit as st
    probe = BookingWriteProbe(auth_client, token, admin_ids)
    probe._authorize()
    st.subheader("Afgrænset skrivetest")
    st.warning("Denne test skriver i samme database som den aktive portal.")
    st.write(f"Kun sæson {TEST_SEASON}, booking {TEST_BOOKING}: {TEST_NAME}.")
    st.caption("Testbookingen er annulleret og uden gæster. Der sendes ingen mail. De øvrige sider er stadig i læsetilstand.")
    st.button("Genindlæs testbooking")
    try:
        row = probe.read()
    except Exception:
        st.error("Testbookingen kunne ikke kontrolleres. Kontrollér login, læseadgang og testnummeret.")
        return
    if row is None:
        st.info("Der er ingen synlig testbooking. SQL-opsætningen skal være kørt før oprettelse.")
        if st.button("Opret annulleret testbooking"):
            try:
                created = probe.create()
                st.success(f"INSERT og genlæsning bekræftet. Testbookingens ID: {created['id']}.")
                st.info("Klik Genindlæs testbooking for at afprøve ændring.")
            except Exception:
                st.error("Oprettelsen kunne ikke bekræftes. Kontrollér SQL-opsætningen og genindlæs før et nyt forsøg.")
        return
    st.write("Testbookingens ID:", row["id"])
    st.write("Gemt kommentar:", row.get("comments") or "")
    with st.form("write_probe_comment", clear_on_submit=True):
        comment = st.text_input("Ny testkommentar", max_chars=500)
        submitted = st.form_submit_button("Gem testkommentar")
    if submitted:
        try:
            updated = probe.update_comment(row["id"], row.get("comments"), comment)
            st.success("UPDATE og genlæsning bekræftet.")
            st.write("Ny gemt kommentar:", updated["comments"])
        except Exception:
            st.error("Ændringen kunne ikke bekræftes. Brug 1–500 tegn, kontrollér SQL-opsætningen og genindlæs.")
