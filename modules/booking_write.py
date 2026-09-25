"""Booking creation through a user-scoped Supabase client; no mail side effects."""
from datetime import date


def create_booking(client, payload):
    payload = dict(payload)
    number = int(payload['booking_number'])
    season = int(payload['season'])
    if number <= 0 or not str(payload.get('navn') or '').strip():
        raise ValueError('Udfyld bookingnummer og navn.')
    if date.fromisoformat(payload['checkout_date']) <= date.fromisoformat(payload['checkin_date']):
        raise ValueError('Checkout skal være efter checkin.')
    payload.update(booking_number=number, season=season)
    existing = (client.table('hk_dtb').select('id').eq('season', season)
                .eq('booking_number', number).limit(1).execute().data or [])
    if existing:
        raise ValueError('Bookingnummeret findes allerede. Brug redigering eller tilføj værelse gennem Timeline.')
    rows = client.table('hk_dtb').insert(payload).execute().data or []
    if len(rows) != 1 or rows[0].get('id') is None:
        raise ValueError('Oprettelsen kunne ikke bekræftes. Kontrollér oversigten før nyt forsøg.')
    row_id = rows[0]['id']
    verified = client.table('hk_dtb').select('id,booking_number,season,navn').eq('id', row_id).execute().data or []
    if (len(verified) != 1 or verified[0].get('booking_number') != number
            or verified[0].get('season') != season or verified[0].get('navn') != payload['navn']):
        raise ValueError('Bookingen kunne ikke genlæses. Kontrollér oversigten før nyt forsøg.')
    return row_id
