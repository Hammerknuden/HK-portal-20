"""Read the same report format from live calculations or frozen season totals."""
import pandas as pd

REPORT_COLUMNS = {
    'room_nights': ['room_nights'],
    'danmarks_statistik': ['country_group', 'arrivals', 'guest_nights'],
    'booking_channels': ['channel', 'room_nights'],
    'returning_guests': ['guest_group', 'room_nights'],
    'gross_revenue_monthly': ['month', 'gross_revenue'],
    'breakfast_monthly': ['month', 'servings', 'net_revenue'],
    'checkins_daily': ['date', 'checkins'],
    'booking_length_monthly': ['month', 'stay_count', 'total_nights'],
}
MONTH_NAMES = dict(enumerate([
    'Januar', 'Februar', 'Marts', 'April', 'Maj', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'December',
], 1))


def read_statistics_history(client):
    rows = []
    while True:
        page = (client.table('statistik_historik').select('*')
                .order('season').order('report_type')
                .range(len(rows), len(rows) + 999).execute().data or [])
        rows.extend(page)
        if len(page) < 1000:
            return rows


def season_reports(client, season, archived, history):
    """Never recalculate an archived year from mutable hk_dtb rows."""
    if archived:
        rows = [r for r in history if int(r['season']) == season]
    else:
        rows = client.rpc('calculate_season_statistics', {'p_season': season}).execute().data or []
    reports = {}
    metadata = {}
    for row in rows:
        name = row['report_type']
        if name not in REPORT_COLUMNS:
            continue
        if row.get('format_version', 1) != 1:
            raise ValueError(f'{season}: ukendt statistikformat for {name}.')
        reports[name] = pd.DataFrame(row['data'], columns=REPORT_COLUMNS[name])
        metadata[name] = row.get('metadata') or {}
    return reports, metadata


def weekday_distribution(checkins):
    """Daily counts keep arbitrary historical period selection possible."""
    weekdays = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']
    counts = (checkins.groupby(checkins['checkin_date'].dt.dayofweek)['checkins']
              .sum().reindex(range(7), fill_value=0))
    total = int(counts.sum())
    return pd.DataFrame({'Ugedag': weekdays, 'Antal': counts.to_numpy(),
                         'Procent': (counts / total * 100 if total else counts.astype(float)).to_numpy()}), total
