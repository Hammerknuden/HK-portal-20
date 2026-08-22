import re
from datetime import datetime
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageOps


MAX_PDF_BYTES = 10 * 1024 * 1024
A4_SIZE_150_DPI = (1240, 1754)
A4_MARGIN_PX = 60


def camera_image_to_pdf(image_bytes):
    """Convert a camera image to a single-page, portrait A4 PDF."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        available_size = (
            A4_SIZE_150_DPI[0] - (2 * A4_MARGIN_PX),
            A4_SIZE_150_DPI[1] - (2 * A4_MARGIN_PX),
        )
        image.thumbnail(available_size, Image.Resampling.LANCZOS)

        page = Image.new("RGB", A4_SIZE_150_DPI, "white")
        position = (
            (A4_SIZE_150_DPI[0] - image.width) // 2,
            (A4_SIZE_150_DPI[1] - image.height) // 2,
        )
        page.paste(image, position)

        output = BytesIO()
        page.save(output, format="PDF", resolution=150.0)
        return output.getvalue()


def validate_pdf(pdf_bytes):
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Filen er ikke en gyldig PDF.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDF-filen er større end 10 MB.")


def build_storage_path(season, booking_number, timestamp=None, unique_id=None):
    """Build a PII-free and collision-resistant path for Storage."""
    booking_number_text = str(booking_number).strip()
    if not re.fullmatch(r"\d+", booking_number_text):
        raise ValueError("Bookingnummer skal bestå af cifre.")
    booking_number_text = f"{int(booking_number_text):03d}"

    timestamp = timestamp or datetime.now()
    unique_id = unique_id or uuid4().hex[:8]
    filename = (
        f"gaesteregistrering_{timestamp:%Y%m%d_%H%M%S}_{unique_id}.pdf"
    )
    return f"test-scans/{int(season)}/{booking_number_text}/{filename}"
