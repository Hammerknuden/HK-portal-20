import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
from auth import require_login
import plotly.express as px
import os
import reportlab
import math
from io import BytesIO
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from portal_access import get_database_client
from modules.season_statistics import (MONTH_NAMES, read_statistics_history, season_reports, weekday_distribution)
from modules.booking_pace import build_booking_pace, fetch_pace_rows, normalize_season_rows


def create_checkin_weekday_pdf(season, middle_start, middle_end, pdf_periods):
    reportlab_fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    if "Vera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Vera", reportlab_fonts / "Vera.ttf"))
        pdfmetrics.registerFont(TTFont("VeraBd", reportlab_fonts / "VeraBd.ttf"))

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Indcheckninger pr. ugedag - sæson {season}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CheckinTitle",
        parent=styles["Title"],
        fontName="VeraBd",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#16324F"),
        spaceAfter=5 * mm,
    )
    subtitle_style = ParagraphStyle(
        "CheckinSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=5 * mm,
    )
    card_title_style = ParagraphStyle(
        "CheckinCardTitle",
        parent=styles["Heading3"],
        fontName="VeraBd",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#16324F"),
        alignment=1,
    )

    story = [
        Paragraph(f"Indcheckninger pr. ugedag - sæson {season}", title_style),
        Paragraph(
            "Midterperiode: "
            f"{middle_start:%d-%m-%Y} - {middle_end:%d-%m-%Y}. "
            "Procenterne beregnes separat inden for hver periode.",
            subtitle_style,
        ),
    ]

    highest_percentage = max(
        (float(distribution["Procent"].max()) for _, distribution, _ in pdf_periods),
        default=0,
    )
    chart_axis_max = max(
        10,
        min(100, math.ceil(highest_percentage * 1.15 / 10) * 10),
    )

    cards = []
    for period_title, distribution, total in pdf_periods:
        chart_drawing = Drawing(74 * mm, 42 * mm)
        bar_chart = VerticalBarChart()
        bar_chart.x = 9 * mm
        bar_chart.y = 8 * mm
        bar_chart.width = 61 * mm
        bar_chart.height = 29 * mm
        bar_chart.data = [distribution["Procent"].tolist()]
        bar_chart.categoryAxis.categoryNames = [
            "Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"
        ]
        bar_chart.categoryAxis.labels.fontName = "Vera"
        bar_chart.categoryAxis.labels.fontSize = 7
        bar_chart.valueAxis.valueMin = 0
        bar_chart.valueAxis.valueMax = chart_axis_max
        bar_chart.valueAxis.valueStep = max(5, chart_axis_max / 5)
        bar_chart.valueAxis.labels.fontName = "Vera"
        bar_chart.valueAxis.labels.fontSize = 6.5
        bar_chart.valueAxis.labelTextFormat = "%d%%"
        bar_chart.valueAxis.visibleGrid = True
        bar_chart.valueAxis.gridStrokeColor = colors.HexColor("#D7E0E7")
        bar_chart.valueAxis.gridStrokeWidth = 0.4
        bar_chart.bars[0].fillColor = colors.HexColor("#2C7DA0")
        bar_chart.bars[0].strokeColor = colors.HexColor("#1B5F7A")
        bar_chart.barSpacing = 2
        bar_chart.groupSpacing = 4
        chart_drawing.add(bar_chart)

        rows = [["Ugedag", "Antal", "Procent"]]
        rows.extend([
            [
                row["Ugedag"],
                str(int(row["Antal"])),
                f'{row["Procent"]:.1f}%',
            ]
            for _, row in distribution.iterrows()
        ])
        data_table = Table(rows, colWidths=[34 * mm, 18 * mm, 22 * mm])
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "VeraBd"),
            ("FONTNAME", (0, 1), (-1, -1), "Vera"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor("#F3F6F8"),
            ]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        card = Table([
            [Paragraph(period_title, card_title_style)],
            [Paragraph(f"<b>{total}</b> indcheckninger", styles["BodyText"])],
            [Spacer(1, 2 * mm)],
            [chart_drawing],
            [data_table],
        ], colWidths=[80 * mm])
        card.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#EAF1F5")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        cards.append(card)

    overview = Table([cards], colWidths=[86 * mm] * 3, hAlign="CENTER")
    overview.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    story.append(overview)
    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()
# -------------------------
# INIT
# -------------------------

st.set_page_config(page_title="Timeline", layout="wide")
require_login()

load_dotenv()

supabase = get_database_client()

st.title("Statistik")
try:
    season_settings = supabase.table("high_season").select("season, pace_archived").order("season").execute().data or []
    season_settings, season_warnings = normalize_season_rows(season_settings, "Sæsonopsætning")
    for message in season_warnings:
        st.warning(message)
    statistics_history = read_statistics_history(supabase)
except Exception as error:
    st.error("Statistik kunne ikke hentes. Kontrollér databaseadgang og at statistikmigrationerne er kørt.")
    st.text(str(error))
    st.stop()

status_by_year = {int(r["season"]): bool(r["pace_archived"]) for r in season_settings if int(r["season"]) >= 2026}
available_years = sorted(set(status_by_year) | {int(r["season"]) for r in statistics_history})
if not available_years:
    st.info("Der er ingen sæsoner at vise.")
    st.stop()
open_years = sorted(y for y, archived in status_by_year.items() if not archived)
active_year = open_years[0] if open_years else available_years[-1]
selected_season = st.selectbox("Vis sæson", available_years, index=available_years.index(active_year))
selected_archived = status_by_year.get(selected_season, True)
st.caption(f"{selected_season}: " + ("Historiske, gemte tal." if selected_archived else "Aktuelle tal – opdateres med bookingerne."))
report_cache = {}


def get_reports(year):
    if year not in report_cache:
        report_cache[year] = season_reports(supabase, year, status_by_year.get(year, True), statistics_history)
    return report_cache[year]


try:
    reports, report_metadata = get_reports(selected_season)
except Exception as error:
    st.error("Statistikberegningen kunne ikke hentes. Kør 20260910_statistics_season_archive.sql i Supabase.")
    st.text(str(error))
    st.stop()


def selected_report(name):
    result = reports.get(name)
    if result is None:
        st.info(f"Denne opgørelse er ikke gemt for {selected_season}." +
                (" Gem sæsonstatistikken i Setup." if selected_season >= 2026 else ""))
    return result


quality = report_metadata.get("room_nights", {})
if quality.get("invalid_rows", 0):
    st.warning(f"{quality['invalid_rows']} rækker har ugyldige statistikoplysninger. Ret data før sæsonafslutning.")
if quality.get("missing_country_rows", 0):
    st.warning(f"{quality['missing_country_rows']} rækker mangler landekode og er udeladt af landefordelingen, men indgår i øvrige tal.")

st.subheader("Rapport til Danmarks Statistik")
st.caption("Annullerede bookinger er filtreret fra. Alle tal i denne opgørelse gælder den valgte sæson.")
room_nights_report = selected_report("room_nights")
if room_nights_report is not None:
    st.metric(f"Solgte værelsesnætter i {selected_season}", f"{int(room_nights_report['room_nights'].sum()):,}".replace(",", "."))
country_report = selected_report("danmarks_statistik")
if country_report is not None:
    st.dataframe(country_report.rename(columns={"country_group": "Land", "arrivals": "Ankomster", "guest_nights": "Overnatninger"}), hide_index=True)

st.subheader(f"Fordeling af solgte værelsesnætter i {selected_season}")
kanal_col, known_col = st.columns(2)
with kanal_col:
    channels = selected_report("booking_channels")
    if channels is not None and not channels.empty:
        st.dataframe(channels.rename(columns={"channel": "Kanal", "room_nights": "Værelsesnætter"}), hide_index=True)
        st.plotly_chart(px.pie(channels, names="channel", values="room_nights", title=f"Bookingkanaler i {selected_season}"), use_container_width=True)
with known_col:
    returning = selected_report("returning_guests")
    if returning is not None and not returning.empty:
        st.dataframe(returning.rename(columns={"guest_group": "Gæstegruppe", "room_nights": "Værelsesnætter"}), hide_index=True)
        st.plotly_chart(px.pie(returning, names="guest_group", values="room_nights", title="Tidligere besøgende blandt egne bookinger"), use_container_width=True)

st.subheader("Booking pace")

pace_step = "Hent sæsonstatus fra high_season"
try:
    pace_seasons = supabase.table("high_season").select("season, pace_archived").execute().data or []
    pace_seasons, season_warnings = normalize_season_rows(pace_seasons, "Sæsonopsætning")
    for message in season_warnings:
        st.warning(message)
    pace_step = "Hent historiske pace-tal fra bookin_pace"
    pace_legacy = fetch_pace_rows(supabase, "bookin_pace", "*")
    pace_history = []
    for season in pace_seasons:
        if int(season["season"]) >= 2026 and season["pace_archived"]:
            pace_step = f"Hent historik for {season['season']} fra historie_new"
            pace_history.extend(fetch_pace_rows(
                supabase, "historie_new",
                "id, season, booking_nr, booking_date, room_nights, web",
                season=int(season["season"]),
            ))
    pace_step = "Hent aktuelle bookinger fra hk_dtb"
    pace_live = fetch_pace_rows(
        supabase, "hk_dtb",
        "id, season, booking_number, booking_date, checkin_date, checkout_date, web",
    )
    pace_step = "Beregn booking pace"
    pace_df, pace_messages = build_booking_pace(
        pace_legacy, pace_history, pace_live, pace_seasons,
    )
    for message in pace_messages:
        st.warning(message)
except Exception as error:
    pace_df = pd.DataFrame()
    st.error(
        "Booking pace kunne ikke hentes. Kontrollér databaseadgang og at "
        "migrationen 20260909_booking_pace_season_status.sql er kørt, "
        "samt at historikken har booking_date og room_nights."
    )
    st.caption(f"Fejlen opstod ved: {pace_step}")
    with st.expander("Tekniske fejldetaljer"):
        st.text(f"{type(error).__name__}: {getattr(error, 'message', str(error))}")

if pace_df.empty:
    st.info("Der er ingen booking pace-data at vise.")
else:
    st.caption(
        "Til og med 2025: historiske pace-tal. Fra 2026: afsluttede sæsoner "
        "fra historikken og åbne sæsoner fra aktuelle bookinger. "
        "Annulleringer fjernes fra hele den åbne sæsons kurve. "
        "Uge 0 viser bookinger fra før sæsonåret; fremtidige sæsoner viser saldoen pr. i dag."
    )
    show_all_pace_years = st.checkbox("Vis alle år", key="pace_show_all_years")
    pace_years = pd.to_numeric(pace_df["season_year"], errors="coerce")
    # The earliest open season stays active until explicitly archived.
    # Creating next year's season must not move the comparison window early.
    open_pace_years = [
        int(row["season"]) for row in pace_seasons
        if int(row["season"]) >= 2026 and not row["pace_archived"]
        and pace_years.eq(int(row["season"])).any()
    ]
    active_pace_year = min(open_pace_years) if open_pace_years else int(pace_years.max())
    if show_all_pace_years:
        visible_pace = pace_df
    else:
        first_pace_year = active_pace_year - 5
        visible_pace = pace_df[pace_years.between(first_pace_year, active_pace_year)]
        st.caption(f"Viser {first_pace_year}–{active_pace_year}: aktiv sæson og de fem foregående sæsoner.")
    fig = px.line(
        visible_pace,
        x="week_number",
        y="sold_nights",
        color="season_year",
        labels={
            "week_number": "Ugenummer",
            "sold_nights": "Solgte værelsesnætter",
            "season_year": "Sæson",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

if st.checkbox("Bruttoomsætning"):
    st.subheader("Omsætning pr. måned inkl. moms – alle sæsoner")
    st.caption("Omsætningen fordeles efter udcheckningsmåned. Afsluttede sæsoner vises med gemte tal; åbne sæsoner opdateres løbende. Ukendte historiske måneder vises som tomme felter.")
    revenue_frames = []
    for year in available_years:
        try:
            year_reports, _ = get_reports(year)
            monthly = year_reports.get("gross_revenue_monthly")
            if monthly is None:
                st.warning(f"Omsætning for {year} er endnu ikke gemt.")
                continue
            monthly = monthly.copy()
            monthly["season"] = str(year)
            revenue_frames.append(monthly)
        except Exception as error:
            st.warning(f"Omsætning for {year} kunne ikke hentes: {error}")
    if revenue_frames:
        revenues = pd.concat(revenue_frames, ignore_index=True)
        revenue_table = revenues.pivot(index="season", columns="month", values="gross_revenue").reindex(columns=range(1, 13))
        st.dataframe(revenue_table.rename(columns=MONTH_NAMES).rename_axis("Sæson").style.format("{:,.2f}", na_rep="–"))
        revenues["Måned"] = revenues["month"].map(MONTH_NAMES)
        st.plotly_chart(px.bar(revenues, x="Måned", y="gross_revenue", color="season", barmode="group",
                              category_orders={"Måned": list(MONTH_NAMES.values())},
                              labels={"gross_revenue": "Bruttoomsætning (kr.)", "season": "Sæson"}), use_container_width=True)

st.subheader(f"Morgenmadsomsætning – {selected_season}")
st.caption("Prebooked morgenmad fratrukket rabat og moms, fordelt på overnatningsdato.")
breakfast = selected_report("breakfast_monthly")
if breakfast is not None:
    st.metric("Omsætning ekskl. moms", f"{breakfast['net_revenue'].sum():,.2f} kr".replace(",", "X").replace(".", ",").replace("X", "."))
    st.caption(f"{int(breakfast['servings'].sum())} morgenmåltider")
    breakfast = breakfast.copy()
    breakfast["month"] = breakfast["month"].map(MONTH_NAMES)
    st.dataframe(breakfast.rename(columns={"month": "Måned", "servings": "Morgenmåltider", "net_revenue": "Nettoomsætning"}), hide_index=True)

st.subheader(f"Sæsonstatistik – {selected_season}")
checkin_report = selected_report("checkins_daily")
checkins = pd.DataFrame(columns=["checkin_date", "checkins"])
if checkin_report is not None:
    checkins = checkin_report.rename(columns={"date": "checkin_date"}).copy()
checkins["checkin_date"] = pd.to_datetime(checkins["checkin_date"])
checkins["checkin_day"] = checkins["checkin_date"].dt.date

st.subheader("Indcheckninger fordelt på ugedage")

if checkins.empty:
    st.info("Der er ingen aktive bookinger med gyldige datoer i den valgte sæson.")
else:
    period_start = checkins["checkin_date"].min().date()
    period_end = checkins["checkin_date"].max().date()
    default_middle_start = max(
        period_start,
        min(datetime.date(selected_season, 6, 27), period_end),
    )
    default_middle_end = max(
        default_middle_start,
        min(datetime.date(selected_season, 8, 10), period_end),
    )

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        middle_start = st.date_input(
            "Midterperiode fra",
            value=default_middle_start,
            min_value=period_start,
            max_value=period_end,
            key=f"checkin_weekday_middle_start_{selected_season}",
        )
    with date_col2:
        middle_end = st.date_input(
            "Midterperiode til",
            value=default_middle_end,
            min_value=period_start,
            max_value=period_end,
            key=f"checkin_weekday_middle_end_{selected_season}",
        )

    if middle_start > middle_end:
        st.error("Startdatoen for midterperioden skal være før slutdatoen.")
    else:
        weekday_order = [
            "Mandag", "Tirsdag", "Onsdag", "Torsdag",
            "Fredag", "Lørdag", "Søndag",
        ]

        periods = [
            (
                f"Før: {period_start:%d-%m-%Y} – "
                f"{middle_start - datetime.timedelta(days=1):%d-%m-%Y}",
                checkins[checkins["checkin_day"] < middle_start],
            ),
            (
                f"Midt: {middle_start:%d-%m-%Y} – {middle_end:%d-%m-%Y}",
                checkins[
                    (checkins["checkin_day"] >= middle_start)
                    & (checkins["checkin_day"] <= middle_end)
                ],
            ),
            (
                f"Efter: {middle_end + datetime.timedelta(days=1):%d-%m-%Y} – "
                f"{period_end:%d-%m-%Y}",
                checkins[checkins["checkin_day"] > middle_end],
            ),
        ]

        pdf_periods = []
        for column, (period_title, period_df) in zip(st.columns(3), periods):
            distribution, total = weekday_distribution(period_df)
            pdf_periods.append((period_title, distribution.copy(), total))
            with column:
                st.markdown(f"**{period_title}**")
                st.caption(f"{total} indcheckninger")
                chart = px.bar(
                    distribution,
                    x="Ugedag",
                    y="Procent",
                    text=distribution["Procent"].map(lambda value: f"{value:.1f}%"),
                    hover_data={"Antal": True, "Procent": ":.1f"},
                    category_orders={"Ugedag": weekday_order},
                )
                chart.update_traces(textposition="outside")
                chart.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Procent",
                    yaxis_range=[0, 100],
                )
                st.plotly_chart(chart, use_container_width=True)
                st.dataframe(
                    distribution.style.format({"Procent": "{:.1f}%"}),
                    hide_index=True,
                    use_container_width=True,
                )

        checkin_pdf = create_checkin_weekday_pdf(
            selected_season,
            middle_start,
            middle_end,
            pdf_periods,
        )
        st.download_button(
            "Download indcheckningsstatistik som PDF",
            data=checkin_pdf,
            file_name=f"indcheckningsstatistik_{selected_season}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

st.subheader("Gennemsnitlig bookinglængde pr. måned")
lengths = selected_report("booking_length_monthly")
if lengths is not None and not lengths.empty:
    lengths = lengths.copy()
    lengths["Måned"] = lengths["month"].map(MONTH_NAMES)
    lengths["Nætter"] = lengths["total_nights"] / lengths["stay_count"].replace(0, float("nan"))
    fig = px.bar(lengths, x="Måned", y="Nætter", text=lengths["Nætter"].round(1),
                 category_orders={"Måned": list(MONTH_NAMES.values())})
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
