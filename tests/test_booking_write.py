import unittest
from unittest.mock import Mock
from modules.booking_write import create_booking

class CreateBookingTests(unittest.TestCase):
    def test_create_and_duplicate_and_failed_readback(self):
        payload=dict(booking_number='302',season=2026,navn='BB',checkin_date='2026-10-02',checkout_date='2026-10-06')
        row=dict(payload,id=221,booking_number=302)
        for results,expected in [([[],[row],[row]],221), ([[row]],None), ([[],[row],[]],None)]:
            client=Mock(); q=client.table.return_value
            for method in ('select','eq','limit','insert'): getattr(q,method).return_value=q
            q.execute.side_effect=[Mock(data=r) for r in results]
            if expected:
                self.assertEqual(create_booking(client,payload),expected)
            else:
                with self.assertRaises(ValueError): create_booking(client,payload)
            if len(results)==1: q.insert.assert_not_called()
    def test_bad_dates_do_not_write(self):
        client=Mock()
        with self.assertRaises(ValueError):
            create_booking(client,dict(booking_number=302,season=2026,navn='BB',checkin_date='2026-10-06',checkout_date='2026-10-02'))
        client.table.assert_not_called()
