from datetime import date
import unittest

import pandas as pd

from modules.in_out_pdf import build_turnover_table, create_turnover_pdf


class TurnoverTests(unittest.TestCase):
    def test_next_arrival_details_and_missing_match(self):
        departures = pd.DataFrame([
            dict(checkout_date="2026-09-03", room_number="2", booking_number="OUT"),
            dict(checkout_date="2026-09-04", room_number="3", booking_number="NONE"),
        ])
        arrivals = pd.DataFrame([
            dict(checkin_date="2026-10-01", room_number=2, nation="SE", bed="Double", enkelt="Nej"),
            dict(checkin_date="2026-09-03", room_number=2, nation="DK", bed="Twin", enkelt="Ja"),
            dict(checkin_date="2026-09-01", room_number=2, nation="DE", bed="Double", enkelt="Nej"),
        ])
        result = build_turnover_table(departures, arrivals)
        self.assertEqual(result.iloc[0]["Booking nr."], "OUT")
        self.assertEqual(result.iloc[0][["Land", "Seng", "Enkelt"]].tolist(), ["DK", "Twin", "Ja"])
        self.assertEqual(result.iloc[0]["Næste indcheck"], pd.Timestamp("2026-09-03"))
        self.assertTrue(pd.isna(result.iloc[1]["Næste indcheck"]))
        self.assertEqual(result.iloc[1]["Land"], "")
        self.assertEqual(departures.iloc[0]["room_number"], "2")
        later = build_turnover_table(departures.iloc[:1], arrivals.iloc[:1])
        self.assertEqual(later.iloc[0]["Land"], "SE")
        self.assertTrue(pd.isna(build_turnover_table(departures, pd.DataFrame()).iloc[0]["Næste indcheck"]))

    def test_pdf_empty_and_multiple_pages(self):
        empty = build_turnover_table(pd.DataFrame(), pd.DataFrame())
        today = date(2026, 9, 3)
        self.assertTrue(create_turnover_pdf(empty, today, today).startswith(b"%PDF-"))
        frame = pd.DataFrame([[today, 12, "123456789012", today, "Danmark", "2 enkeltsenge", "Nej"]] * 45, columns=empty.columns)
        pdf = create_turnover_pdf(frame, today, today)
        self.assertTrue(pdf.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
