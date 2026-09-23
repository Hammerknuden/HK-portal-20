import unittest
from testing.write_probe import is_booking_300_patch

class Booking300ScopeTests(unittest.TestCase):
    def setUp(self):
        self.params = {'id':['eq.218'], 'season':['eq.2026'], 'booking_number':['eq.300'], 'navn':['eq.NN']}
        self.payload = dict.fromkeys(['booking_number','familie_navn','email','telefon','checkin_date','checkout_date','nation','web','ankomst','bed','morgenmad','room_number','season'], '')
        self.payload.update(booking_number='300', season='2026', checkin_date='2026-10-01', checkout_date='2026-10-04')
    def allowed(self, method='PATCH', path='/rest/v1/hk_dtb'):
        return is_booking_300_patch(method,path,self.params,self.payload)
    def test_valid_edit(self):
        self.assertTrue(self.allowed())
    def test_wrong_scope(self):
        for key in ('id','season','booking_number','navn'):
            saved=self.params.pop(key)
            self.assertFalse(self.allowed())
            self.params[key]=saved
        self.params['or']=['(id.eq.1,id.eq.218)']
        self.assertFalse(self.allowed())
    def test_other_operations(self):
        for method in ('POST','DELETE','PUT'):
            self.assertFalse(self.allowed(method))
        self.assertFalse(self.allowed(path='/rest/v1/historie_new'))
    def test_invalid_dates_or_identity(self):
        for key,value in [('season','2027'),('booking_number','301'),('checkin_date','2026-09-30'),('checkout_date','2026-11-02'),('checkout_date','2026-10-01')]:
            old=self.payload[key]
            self.payload[key]=value
            self.assertFalse(self.allowed())
            self.payload[key]=old
    def test_extra_column_rejected(self):
        self.payload['id']=1
        self.assertFalse(self.allowed())
