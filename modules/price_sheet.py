from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BLUE = colors.HexColor("#2F75B5")


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _short_date(value):
    return f"{value.day}/{value.month}"


def _dkk(value):
    amount = float(value)
    if amount.is_integer():
        return f"DKK {int(amount):,}".replace(",", ".")
    return f"DKK {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def create_price_sheet_pdf(price_row, logo_path=None):
    """Return an A4 PDF containing the saved prices for one season."""
    season = int(price_row["season"])
    high_start = _as_date(price_row["start_season"])
    high_end = _as_date(price_row["end_season"])
    low_start = date(season, 5, 1)
    low_end = date(season, 10, 4)

    low_periods = []
    if low_start < high_start:
        low_periods.append(
            f"{_short_date(low_start)} - {_short_date(high_start - timedelta(days=1))}"
        )
    if high_end < low_end:
        low_periods.append(
            f"{_short_date(high_end + timedelta(days=1))} - {_short_date(low_end)}"
        )
    low_season_text = " & ".join(low_periods) or "Ingen"
    high_season_text = f"{_short_date(high_start)} - {_short_date(high_end)}"

    breakfast = float(price_row["pris_morgenmad"])
    single_low = float(price_row["enk_low"])
    single_high = float(price_row["enk_high"])
    double_low = float(price_row["dobb_low"])
    double_high = float(price_row["dobb_high"])

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Prisskema {season}",
        author="Hammerknuden Sommerpension",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PriceTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_LEFT,
        spaceAfter=8 * mm,
    )
    body_style = ParagraphStyle(
        "PriceBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
    )
    bold_style = ParagraphStyle(
        "PriceBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    elements = []
    if logo_path and Path(logo_path).is_file():
        logo = Image(str(logo_path))
        logo.drawWidth = 75 * mm
        logo.drawHeight = logo.drawWidth * logo.imageHeight / logo.imageWidth
        logo.hAlign = "LEFT"
        elements.extend([logo, Spacer(1, 4 * mm)])

    elements.append(Paragraph(f"PRISER 1. MAJ - 4. OKTOBER {season}", title_style))

    def p(text, bold=False):
        return Paragraph(str(text), bold_style if bold else body_style)

    table_data = [
        [
            p("DOBBELTVÆRELSE for 2 personer", True),
            p(f"Lavsæson<br/>{low_season_text}", True),
            p(f"Højsæson<br/>{high_season_text}", True),
        ],
        [p("Dobbeltværelse uden morgenmad"), p(_dkk(double_low)), p(_dkk(double_high))],
        [
            p("Dobbeltværelse med morgenmad"),
            p(_dkk(double_low + breakfast * 2)),
            p(_dkk(double_high + breakfast * 2)),
        ],
        [p(""), p(""), p("")],
        [p("ENKELTVÆRELSE<br/>(Dobbeltværelse for 1 person)", True), p(""), p("")],
        [p("Enkeltværelse uden morgenmad"), p(_dkk(single_low)), p(_dkk(single_high))],
        [
            p("Enkeltværelse med morgenmad"),
            p(_dkk(single_low + breakfast)),
            p(_dkk(single_high + breakfast)),
        ],
        [p(""), p(""), p("")],
        [
            p("Tilkøb morgenmad"),
            p(f"{_dkk(breakfast)}/person"),
            p(f"{_dkk(breakfast)}/person"),
        ],
    ]

    table = Table(
        table_data,
        colWidths=[76 * mm, 52 * mm, 48 * mm],
        rowHeights=[
            25 * mm,
            17 * mm,
            17 * mm,
            7 * mm,
            20 * mm,
            17 * mm,
            17 * mm,
            7 * mm,
            18 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.8, BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("SPAN", (0, 4), (0, 4)),
            ]
        )
    )
    elements.extend(
        [
            table,
            Spacer(1, 7 * mm),
            Paragraph(
                "Send forespørgsel vedr. reservation – vi svarer så hurtigt, som vi kan.",
                body_style,
            ),
        ]
    )

    document.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
