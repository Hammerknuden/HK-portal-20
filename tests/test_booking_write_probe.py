import unittest
from unittest.mock import Mock, patch

from testing.write_probe import BookingWriteProbe, TEST_NAME, is_scoped_comment_patch, save_booking_test_comment


class TestBookingWriteProbe(unittest.TestCase):
    def test_transport_accepts_only_reserved_comment_patch(self):
        params = {"id": ["eq.217"], "season": ["eq.2099"], "booking_number": ["eq.99999"],
                  "navn": ["eq." + TEST_NAME], "web": ["eq.cansl"]}
        allowed = lambda method, p, body: is_scoped_comment_patch(method, "/rest/v1/hk_dtb", p, body)
        self.assertTrue(allowed("PATCH", params, {"comments": "Test"}))
        for method in ("POST", "DELETE", "PUT"):
            self.assertFalse(allowed(method, params, {"comments": "Test"}))
        for key in params:
            self.assertFalse(allowed("PATCH", {k:v for k,v in params.items() if k != key}, {"comments": "Test"}))
        self.assertFalse(allowed("PATCH", {**params, "season": ["eq.2026"]}, {"comments": "Test"}))
        self.assertFalse(allowed("PATCH", {**params, "or": ["(id.eq.1)"]}, {"comments": "Test"}))
        self.assertFalse(allowed("PATCH", {**params, "id": ["eq.217", "eq.1"]}, {"comments": "Test"}))
        self.assertFalse(allowed("PATCH", params, {"comments": "Test", "web": "bc"}))

    def test_sdk_update_is_scoped_and_verified(self):
        client = Mock()
        table = client.table.return_value
        update = table.update.return_value
        update.eq.return_value = update
        update.is_.return_value = update
        update.execute.return_value.data = [{"id": 217, "comments": "Test"}]
        read = table.select.return_value
        read.eq.return_value = read
        read.execute.return_value.data = [{"id": 217, "comments": "Test"}]
        save_booking_test_comment(client, 217, None, "Test")
        table.update.assert_called_once_with({"comments": "Test"})
        update.eq.assert_any_call("id", 217)
        update.eq.assert_any_call("season", 2099)
        update.eq.assert_any_call("booking_number", 99999)
        update.is_.assert_called_once_with("comments", "null")
        read.execute.assert_called_once()
        update.execute.return_value.data = []
        with self.assertRaises(ValueError):
            save_booking_test_comment(client, 217, None, "Test")

    def setUp(self):
        self.auth = Mock(rest_url="https://example.supabase.co/rest/v1", key="sb_publishable_test")
        self.auth.get_user.return_value = {"id": "admin"}
        self.probe = BookingWriteProbe(self.auth, "user-jwt", ["admin"])
        self.row = {"id": 123, "navn": TEST_NAME, "web": "cansl", "comments": "before"}

    def response(self, rows):
        response = Mock()
        response.json.return_value = rows
        return response

    @patch("testing.write_probe.requests.request")
    def test_ordinary_user_cannot_reach_table(self, request):
        self.auth.get_user.return_value = {"id": "ordinary"}
        with self.assertRaises(PermissionError):
            self.probe.create()
        request.assert_not_called()

    @patch("testing.write_probe.requests.request")
    def test_create_is_fixed_cancelled_booking_and_verified(self, request):
        request.side_effect = [self.response([]), self.response([{"id": 123}]), self.response([self.row])]
        self.assertEqual(self.probe.create()["id"], 123)
        call = request.call_args_list[1]
        self.assertEqual(call.args, ("POST", "https://example.supabase.co/rest/v1/hk_dtb"))
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer user-jwt")
        self.assertEqual(call.kwargs["headers"]["apikey"], "sb_publishable_test")
        payload = call.kwargs["json"]
        self.assertEqual((payload["season"], payload["booking_number"]), (2099, 99999))
        self.assertEqual((payload["web"], payload["numb_guests"]), ("cansl", 0))
        self.assertNotIn("id", payload)
        self.assertNotIn("email", payload)
        self.assertEqual(request.call_args_list[2].args[0], "GET")

    @patch("testing.write_probe.requests.request")
    def test_existing_booking_is_not_inserted_again(self, request):
        request.return_value = self.response([self.row])
        with self.assertRaises(ValueError):
            self.probe.create()
        self.assertEqual(request.call_count, 1)

    @patch("testing.write_probe.requests.request")
    def test_collision_or_duplicates_fail_before_write(self, request):
        for rows in [[{**self.row, "navn": "Real guest"}], [self.row, self.row]]:
            request.reset_mock()
            request.return_value = self.response(rows)
            with self.assertRaises(ValueError):
                self.probe.create()
            self.assertEqual(request.call_count, 1)

    @patch("testing.write_probe.requests.request")
    def test_update_only_sends_comment_with_exact_filters_and_readback(self, request):
        updated = {**self.row, "comments": "after"}
        request.side_effect = [self.response([self.row]), self.response([updated]), self.response([updated])]
        self.assertEqual(self.probe.update_comment(123, "before", "after"), updated)
        call = request.call_args_list[1]
        self.assertEqual(call.args[0], "PATCH")
        self.assertEqual(call.kwargs["json"], {"comments": "after"})
        self.assertEqual(call.kwargs["params"]["id"], "eq.123")
        self.assertEqual(call.kwargs["params"]["comments"], "eq.before")
        self.assertEqual(call.kwargs["params"]["booking_number"], "eq.99999")

    @patch("testing.write_probe.requests.request")
    def test_wrong_id_and_stale_comment_are_not_written(self, request):
        request.return_value = self.response([self.row])
        for row_id, before in [(456, "before"), (123, "stale")]:
            with self.assertRaises(ValueError):
                self.probe.update_comment(row_id, before, "after")
        self.assertTrue(all(c.args[0] == "GET" for c in request.call_args_list))

    @patch("testing.write_probe.requests.request")
    def test_rls_empty_update_is_not_reported_as_success(self, request):
        request.side_effect = [self.response([self.row]), self.response([])]
        with self.assertRaises(ValueError):
            self.probe.update_comment(123, "before", "after")

    @patch("testing.write_probe.requests.request")
    def test_invalid_comment_never_calls_network(self, request):
        for comment in ["", "  ", "x" * 501]:
            with self.assertRaises(ValueError):
                self.probe.update_comment(123, "before", comment)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
