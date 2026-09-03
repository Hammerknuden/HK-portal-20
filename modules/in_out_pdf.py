from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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


def build_turnover_table(departures, arrivals):
    """Keep each departure and add details from its room's next arrival."""
    columns = ["Udcheck", "Værelse", "Booking nr.", "Næste indcheck", "Land", "Seng", "Enkelt"]
    if departures.empty:
        return pd.DataFrame(columns=columns)
    outgoing = departures.copy()
    incoming = arrivals.copy()
    outgoing["checkout_date"] = pd.to_datetime(outgoing["checkout_date"], errors="coerce")
    outgoing["room_number"] = pd.to_numeric(outgoing["room_number"], errors="coerce").astype("Int64")
    if not incoming.empty:
        incoming["checkin_date"] = pd.to_datetime(incoming["checkin_date"], errors="coerce")
        incoming["room_number"] = pd.to_numeric(incoming["room_number"], errors="coerce").astype("Int64")
        incoming = incoming.sort_values("checkin_date", kind="stable")
    rows = []
    for _, departure in outgoing.sort_values(["checkout_date", "room_number"]).iterrows():
        details = [pd.NaT, "", "", ""]
        if not incoming.empty:
            matches = incoming[
                (incoming["room_number"] == departure["room_number"])
                & (incoming["checkin_date"] >= departure["checkout_date"])
            ]
            if not matches.empty:
                next_arrival = matches.iloc[0]
                details = [next_arrival.get(key, "") for key in ("checkin_date", "nation", "bed", "enkelt")]
        rows.append([departure["checkout_date"], departure["room_number"], departure["booking_number"], *details])
    return pd.DataFrame(rows, columns=columns)


def create_turnover_pdf(frame, period_start, period_end):
    """Large-print room turnover list; never shrink text to fit more rows."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title="Værelsesskift - stor skrift",
        author="Hammerknuden Sommerpension",
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("TurnoverCell", fontName="Helvetica", fontSize=14, leading=17)
    header = ParagraphStyle("TurnoverHeader", parent=cell, fontName="Helvetica-Bold")
    story = [
        Paragraph("Værelsesskift - afrejse og næste ankomst", styles["Heading1"]),
        Paragraph(f"Periode: {period_start:%d-%m-%Y} - {period_end:%d-%m-%Y}", styles["Normal"]),
        Paragraph("Booking nr. gælder den afrejsende. Land, seng og enkelt gælder den næste ankommende.", styles["Normal"]),
        Spacer(1, 5 * mm),
    ]
    if frame.empty:
        story.append(Paragraph("Ingen udcheckninger i perioden.", cell))
    else:
        story.append(_styled_table(frame, header, cell, [width * mm for width in (36, 25, 46, 43, 33, 46, 38)]))
    document.build(story)
    return buffer.getvalue()


def _cell_text(value):
    if pd.isna(value):
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    return str(value)


def _table_data(frame, header_style, cell_style):
    rows = [[Paragraph(str(column), header_style) for column in frame.columns]]
    for row in frame.itertuples(index=False, name=None):
        rows.append([Paragraph(_cell_text(value), cell_style) for value in row])
    return rows


def _styled_table(frame, header_style, cell_style, col_widths=None):
    table = Table(
        _table_data(frame, header_style, cell_style),
        repeatRows=1,
        colWidths=col_widths,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def create_in_out_pdf(
    arrivals,
    departures,
    report_date=None,
    period_start=None,
    period_end=None,
    logo_path=None,
):
    """Create the print-ready arrivals and departures PDF."""
    report_date = report_date or date.today()
    period_start = period_start or report_date
    period_end = period_end or report_date

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Ankomster og afrejser {report_date.isoformat()}",
        author="Hammerknuden Sommerpension",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InOutTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        spaceAfter=3 * mm,
    )
    meta_style = ParagraphStyle(
        "InOutMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
    )
    header_style = ParagraphStyle(
        "InOutHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10.5,
    )
    cell_style = ParagraphStyle(
        "InOutCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
    )

    story = []
    if logo_path and Path(logo_path).is_file():
        logo = Image(str(logo_path))
        logo.drawWidth = 55 * mm
        logo.drawHeight = logo.drawWidth * logo.imageHeight / logo.imageWidth
        logo.hAlign = "LEFT"
        story.extend([logo, Spacer(1, 3 * mm)])

    story.extend(
        [
            Paragraph("Ankomster og afrejser", title_style),
            Paragraph(
                f"Rapportdato: {report_date.strftime('%d-%m-%Y')}<br/>"
                f"Periode: {period_start.strftime('%d-%m-%Y')} - "
                f"{period_end.strftime('%d-%m-%Y')}",
                meta_style,
            ),
            Spacer(1, 5 * mm),
        ]
    )

    if not arrivals.empty:
        story.append(Paragraph("Ankomster", styles["Heading2"]))
        arrival_widths = None
        if len(arrivals.columns) == 10:
            arrival_widths = [
                21 * mm,
                30 * mm,
                18 * mm,
                45 * mm,
                15 * mm,
                25 * mm,
                18 * mm,
                17 * mm,
                16 * mm,
                66 * mm,
            ]
        story.append(
            _styled_table(arrivals, header_style, cell_style, arrival_widths)
        )
        story.append(Spacer(1, 6 * mm))

    if not departures.empty:
        story.append(Paragraph("Afrejser", styles["Heading2"]))
        departure_widths = [35 * mm, 28 * mm, 38 * mm, 38 * mm]
        story.append(
            _styled_table(departures, header_style, cell_style, departure_widths)
        )

    if arrivals.empty and departures.empty:
        story.append(Paragraph("Ingen ankomster eller afrejser i perioden.", meta_style))

    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()
