from datetime import datetime
from io import BytesIO
import unittest

from PIL import Image
from pypdf import PdfReader, PdfWriter

from modules.guest_scan import (
    build_storage_path,
    camera_image_to_pdf,
    normalize_pdf_to_a4,
    validate_pdf,
)


class GuestScanTests(unittest.TestCase):
    def test_camera_image_is_converted_to_pdf(self):
        image = Image.new("RGB", (800, 1200), "white")
        source = BytesIO()
        image.save(source, format="JPEG")

        pdf = camera_image_to_pdf(source.getvalue())

        self.assertTrue(pdf.startswith(b"%PDF-"))
        validate_pdf(pdf)

    def test_storage_path_contains_no_guest_name(self):
        path = build_storage_path(
            2026,
            "113",
            timestamp=datetime(2026, 8, 22, 14, 30, 5),
            unique_id="abc12345",
        )

        self.assertEqual(
            path,
            "test-scans/2026/113/"
            "gaesteregistrering_20260822_143005_abc12345.pdf",
        )

    def test_storage_path_rejects_non_numeric_booking_number(self):
        with self.assertRaisesRegex(ValueError, "cifre"):
            build_storage_path(2026, "113/test")

    def test_short_booking_number_is_zero_padded(self):
        path = build_storage_path(
            2026,
            13,
            timestamp=datetime(2026, 8, 22, 14, 30, 5),
            unique_id="abc12345",
        )

        self.assertIn("test-scans/2026/013/", path)

    def test_a5_pdf_is_scaled_to_a4(self):
        source = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=419.5276, height=595.2756)
        writer.write(source)

        normalized = normalize_pdf_to_a4(source.getvalue())
        page = PdfReader(BytesIO(normalized)).pages[0]

        self.assertAlmostEqual(float(page.mediabox.width), 595.2756, places=2)
        self.assertAlmostEqual(float(page.mediabox.height), 841.8898, places=2)


if __name__ == "__main__":
    unittest.main()
