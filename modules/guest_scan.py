import re
from io import BytesIO

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pypdf import PageObject, PdfReader, PdfWriter, Transformation


MAX_PDF_BYTES = 10 * 1024 * 1024
A4_RENDER_DPI = 300
A4_SIZE_PX = (2480, 3508)
A4_MARGIN_PX = 100
A4_SIZE_POINTS = (595.2756, 841.8898)
A4_MARGIN_POINTS = 24


def camera_image_to_pdf(image_bytes):
    """Enhance a camera image and convert it to a 300 DPI portrait A4 PDF."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image = ImageOps.autocontrast(image, cutoff=1)
        image = ImageEnhance.Contrast(image).enhance(1.12)
        image = image.filter(
            ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=3)
        )
        available_size = (
            A4_SIZE_PX[0] - (2 * A4_MARGIN_PX),
            A4_SIZE_PX[1] - (2 * A4_MARGIN_PX),
        )
        scale = min(
            available_size[0] / image.width,
            available_size[1] / image.height,
        )
        scaled_size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        image = image.resize(scaled_size, Image.Resampling.LANCZOS)

        page = Image.new("RGB", A4_SIZE_PX, "white")
        position = (
            (A4_SIZE_PX[0] - image.width) // 2,
            (A4_SIZE_PX[1] - image.height) // 2,
        )
        page.paste(image, position)

        output = BytesIO()
        page.save(output, format="PDF", resolution=A4_RENDER_DPI, quality=95)
        return output.getvalue()


def validate_pdf(pdf_bytes):
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Filen er ikke en gyldig PDF.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDF-filen er større end 10 MB.")


def normalize_pdf_to_a4(pdf_bytes):
    """Scale every source page proportionally onto a portrait A4 page."""
    validate_pdf(pdf_bytes)
    reader = PdfReader(BytesIO(pdf_bytes))
    if not reader.pages:
        raise ValueError("PDF-filen indeholder ingen sider.")

    a4_width, a4_height = A4_SIZE_POINTS
    available_width = a4_width - (2 * A4_MARGIN_POINTS)
    available_height = a4_height - (2 * A4_MARGIN_POINTS)
    writer = PdfWriter()

    for source_page in reader.pages:
        source_width = float(source_page.mediabox.width)
        source_height = float(source_page.mediabox.height)
        if source_width <= 0 or source_height <= 0:
            raise ValueError("PDF-filen har en ugyldig sidestørrelse.")

        scale = min(
            available_width / source_width,
            available_height / source_height,
        )
        offset_x = (a4_width - (source_width * scale)) / 2
        offset_y = (a4_height - (source_height * scale)) / 2

        source_page.add_transformation(
            Transformation()
            .scale(scale, scale)
            .translate(offset_x, offset_y)
        )
        a4_page = PageObject.create_blank_page(
            width=a4_width,
            height=a4_height,
        )
        a4_page.merge_page(source_page)
        writer.add_page(a4_page)

    output = BytesIO()
    writer.write(output)
    normalized = output.getvalue()
    validate_pdf(normalized)
    return normalized


def build_storage_path(season, booking_number):
    """Build the canonical PDF path for one guest registration per booking."""
    season_text = str(season).strip()
    if not re.fullmatch(r"\d{4}", season_text):
        raise ValueError("Sæson skal være et firecifret årstal.")

    booking_number_text = str(booking_number).strip()
    if not re.fullmatch(r"\d+", booking_number_text):
        raise ValueError("Bookingnummer skal bestå af cifre.")
    booking_number_text = f"{int(booking_number_text):03d}"

    return f"{season_text}/{season_text}-{booking_number_text}.pdf"
