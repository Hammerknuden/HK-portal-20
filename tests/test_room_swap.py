import unittest
from unittest.mock import Mock, patch
from modules.room_swap import execute_room_swap
class RoomSwapTests(unittest.TestCase):
    def test_supabase_uses_one_rpc_and_no_separate_updates(self):
        client=Mock(); client.rpc.return_value.execute.return_value.data={'success':True,'updated':2}
        with patch.dict('sys.modules',{'portal_access':Mock(uses_supabase_auth=lambda:True)}):
            self.assertTrue(execute_room_swap(client,[1],[2],3,5)['success'])
        client.table.assert_not_called()
        client.rpc.assert_called_once_with('swap_booking_rooms',{'p_a':[1],'p_b':[2],'p_room_a':3,'p_room_b':5})
    def test_failed_rpc_has_no_fallback_updates(self):
        client=Mock(); client.rpc.return_value.execute.side_effect=ValueError('conflict')
        with patch.dict('sys.modules',{'portal_access':Mock(uses_supabase_auth=lambda:True)}):
            with self.assertRaises(ValueError): execute_room_swap(client,[1],[2],3,5)
        client.table.assert_not_called()
    def test_legacy_path_preserved(self):
        client=Mock()
        with patch.dict('sys.modules',{'portal_access':Mock(uses_supabase_auth=lambda:False)}):
            self.assertTrue(execute_room_swap(client,[1],[2],3,5)['success'])
        client.rpc.assert_not_called()
        self.assertEqual(client.table.call_count,2)
