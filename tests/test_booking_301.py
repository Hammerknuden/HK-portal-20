import unittest
from unittest.mock import Mock
from testing.write_probe import BOOKING_301_FIELDS, is_booking_301_insert, create_booking_301

class Booking301Tests(unittest.TestCase):
    def setUp(self):
        self.payload=dict.fromkeys(BOOKING_301_FIELDS,'')
        self.payload.update(booking_number='301',navn='AA',season=2026,
            checkin_date='2026-10-02',checkout_date='2026-10-06',numb_rooms=1,room_number=7)
    def valid(self):
        return is_booking_301_insert('POST','/rest/v1/hk_dtb',{},self.payload)
    def test_scope(self):
        self.assertTrue(self.valid())
        for key,value in [('navn','NN'),('season',2027),('booking_number','302'),
                          ('checkin_date','2026-10-01'),('checkout_date','2026-10-07'),
                          ('numb_rooms',2),('room_number',1)]:
            old=self.payload[key]; self.payload[key]=value
            self.assertFalse(self.valid()); self.payload[key]=old
        self.assertFalse(is_booking_301_insert('POST','/rest/v1/hk_dtb',{'on_conflict':['id']},self.payload))
        self.assertFalse(is_booking_301_insert('PATCH','/rest/v1/hk_dtb',{},self.payload))
        self.assertFalse(is_booking_301_insert('POST','/rest/v1/hk_dtb',{},[self.payload]))
    def client(self, results):
        client=Mock(); query=client.table.return_value
        query.select.return_value=query; query.eq.return_value=query; query.insert.return_value=query
        query.execute.side_effect=[Mock(data=r) for r in results]
        return client,query
    def test_insert_and_readback(self):
        row={**self.payload,'id':219}
        client,query=self.client([[],[row],[row]])
        self.assertEqual(create_booking_301(client,self.payload),219)
        query.insert.assert_called_once_with(self.payload)
    def test_duplicate_rejected_before_insert(self):
        client,query=self.client([[{'id':219}]])
        with self.assertRaises(ValueError): create_booking_301(client,self.payload)
        query.insert.assert_not_called()
    def test_empty_or_mismatched_result_rejected(self):
        row={**self.payload,'id':219}
        for inserted,readback in [([],[]),([row],[]),([row],[{**row,'id':220}])]:
            client,_=self.client([[],inserted,readback])
            with self.assertRaises(ValueError): create_booking_301(client,self.payload)
