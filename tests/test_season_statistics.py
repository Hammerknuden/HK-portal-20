"""Season display tests with synthetic data; no network or production database."""
from copy import deepcopy
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest
from modules.season_statistics import REPORT_COLUMNS, season_reports, weekday_distribution


def reports_for(year, total=4):
    data = {
        'room_nights': [{'room_nights': total}],
        'danmarks_statistik': [{'country_group': 'DK', 'arrivals': 2, 'guest_nights': 4}],
        'booking_channels': [{'channel': 'Egne bookinger', 'room_nights': total}],
        'returning_guests': [{'guest_group': 'Tidligere besøgende', 'room_nights': total}],
        'gross_revenue_monthly': [{'month': m, 'gross_revenue': 1000 if m == 6 else 0} for m in range(1, 13)],
        'breakfast_monthly': [{'month': m, 'servings': 2 if m == 6 else 0, 'net_revenue': 144 if m == 6 else 0} for m in range(1, 13)],
        'checkins_daily': [{'date': f'{year}-06-01', 'checkins': 2}, {'date': f'{year}-07-01', 'checkins': 3}],
        'booking_length_monthly': [{'month': 6, 'stay_count': 2, 'total_nights': total}],
    }
    return [dict(season=year, report_type=k, data=v, metadata={}, format_version=1) for k,v in data.items()]


class Query:
    def __init__(self, rows): self.rows = deepcopy(rows)
    def select(self, *a): return self
    def order(self, *a): return self
    def eq(self, col, value):
        self.rows = [r for r in self.rows if r.get(col) == value]
        return self
    def range(self, start, end):
        self.rows = self.rows[start:end+1]
        return self
    def execute(self): return SimpleNamespace(data=self.rows)


class Client:
    def __init__(self):
        self.calls = []
        self.history = reports_for(2026, 8)
        self.tables = {
            'high_season': [dict(season=2026, pace_archived=True), dict(season=2027, pace_archived=False)],
            'statistik_historik': self.history,
            'bookin_pace': [dict(id=1, season_year=2025, week_number=1, sold_nights=2)],
            'historie_new': [dict(id=1, season=2026, booking_nr=1, booking_date='2026-01-01', room_nights=8, web='web')],
            'hk_dtb': [],
        }
    def table(self, name): return Query(self.tables[name])
    def rpc(self, name, params):
        self.calls.append((name, params))
        return Query(reports_for(params['p_season']))


class SeasonStatisticsTests(unittest.TestCase):
    def test_archived_reads_only_saved_totals(self):
        client = Client()
        reports, _ = season_reports(client, 2026, True, client.history)
        self.assertEqual(reports['room_nights'].iloc[0].room_nights, 8)
        self.assertEqual(client.calls, [])

    def test_missing_archive_is_not_recalculated(self):
        client = Client()
        reports, _ = season_reports(client, 2026, True, [])
        self.assertEqual(reports, {})
        self.assertEqual(client.calls, [])

    def test_open_season_uses_live_calculation(self):
        client = Client()
        reports, _ = season_reports(client, 2027, False, client.history)
        self.assertEqual(reports['room_nights'].iloc[0].room_nights, 4)
        self.assertEqual(client.calls[0][1], {'p_season': 2027})

    def test_daily_counts_are_weighted_not_counted_as_single_arrival(self):
        df = pd.DataFrame({'checkin_date': pd.to_datetime(['2026-06-01', '2026-06-08', '2026-06-02']), 'checkins': [4, 3, 2]})
        result, total = weekday_distribution(df)
        self.assertEqual(total, 9)
        self.assertEqual(result.iloc[0]['Antal'], 7)
        empty, total = weekday_distribution(df.iloc[:0])
        self.assertEqual(total, 0)
        self.assertEqual(empty.Procent.sum(), 0)

    def test_page_season_switch_revenue_and_pdf(self):
        client = Client()
        auth = ModuleType('auth'); auth.require_login = lambda: None
        access = ModuleType('portal_access'); access.get_database_client = lambda: client
        with patch.dict('sys.modules', {'auth': auth, 'portal_access': access}):
            app = AppTest.from_file('pages/8_statestik.py', default_timeout=30).run()
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertEqual(app.selectbox[0].value, 2027)
            self.assertEqual(app.metric[0].value, '4')
            app.selectbox[0].select(2026).run()
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertEqual(app.metric[0].value, '8')
            self.assertTrue(all(params['p_season'] != 2026 for _,params in client.calls))
            next(c for c in app.checkbox if c.label == 'Bruttoomsætning').check().run()
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertEqual(len(app.get('download_button')), 1)

    def test_legacy_revenue_only_does_not_fabricate_other_reports(self):
        client = Client()
        legacy = next(r for r in reports_for(2024) if r['report_type'] == 'gross_revenue_monthly')
        legacy['data'] = [r for r in legacy['data'] if 5 <= r['month'] <= 9]
        client.tables['statistik_historik'].append(legacy)
        auth = ModuleType('auth'); auth.require_login = lambda: None
        access = ModuleType('portal_access'); access.get_database_client = lambda: client
        with patch.dict('sys.modules', {'auth': auth, 'portal_access': access}):
            app = AppTest.from_file('pages/8_statestik.py', default_timeout=30).run()
            app.selectbox[0].select(2024).run()
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertTrue(any('ikke gemt' in i.value for i in app.info))
            self.assertFalse(any('Solgte værelsesnætter' in m.label for m in app.metric))


if __name__ == '__main__': unittest.main()
