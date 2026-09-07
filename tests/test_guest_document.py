import unittest
from unittest.mock import Mock
from modules.guest_document import download_registration


class TestGuestDocument(unittest.TestCase):
    def test_denied_user_never_reads_storage(self):
        client = Mock()
        with self.assertRaises(PermissionError):
            download_registration(client, "2025/2025-148.pdf", Mock(side_effect=PermissionError))
        client.storage.from_.assert_not_called()

    def test_download_uses_private_bucket_and_exact_path(self):
        client = Mock()
        client.storage.from_.return_value.download.return_value = b"%PDF-1.7\nexample"
        authorize = Mock()
        name, data = download_registration(client, "2025/2025-148.pdf", authorize)
        authorize.assert_called_once()
        client.storage.from_.assert_called_once_with("guest-registrations")
        client.storage.from_.return_value.download.assert_called_once_with("2025/2025-148.pdf")
        self.assertEqual(name, "2025-148.pdf")
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_invalid_paths_are_not_requested(self):
        for path in [None, "../file.pdf", "/file.pdf", "https://example/file.pdf", "2025\\file.pdf"]:
            client = Mock()
            with self.assertRaises(ValueError):
                download_registration(client, path, Mock())
            client.storage.from_.assert_not_called()

    def test_non_pdf_is_not_served(self):
        client = Mock()
        client.storage.from_.return_value.download.return_value = b"<html>error</html>"
        with self.assertRaises(ValueError):
            download_registration(client, "file.pdf", Mock())


if __name__ == "__main__":
    unittest.main()
