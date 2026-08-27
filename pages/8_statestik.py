import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
from auth import require_login
from common import init_session, exclude_cancelled_bookings
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
from supabase import create_client


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

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

try:
    all_rows = []
    offset = 0
    page_size = 1000

    while True:
        response = (
            supabase.table("hk_dtb")
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )

        if not response.data:
            break

        all_rows.extend(response.data)
        offset += page_size

    df = pd.DataFrame(all_rows)

    # Fjern annullerede bookinger
    df = exclude_cancelled_bookings(df)

    # Beregn antal nætter
    df["checkin_date"] = pd.to_datetime(df["checkin_date"])
    df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    df["nights"] = (
        df["checkout_date"] - df["checkin_date"]
    ).dt.days.clip(lower=0)

    # En række repræsenterer ét solgt værelse. Summen af nights er derfor
    # solgte værelsesnætter (i modsætning til gæsteovernatninger nedenfor).
    booking_seasons = pd.to_numeric(df["season"], errors="coerce")
    sold_room_nights_2026 = int(
        pd.to_numeric(
            df.loc[booking_seasons.eq(2026), "nights"], errors="coerce"
        ).fillna(0).sum()
    )

    df["overnatninger"] = (
        pd.to_numeric(df["numb_guests"], errors="coerce").fillna(0)
        * df["nights"]
    )
    bookings_df = df.copy()
    df["nation"] = (
        df["nation"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df[df["nation"] != ""]
    # Statistik pr. land
    stats = (
        df.groupby("nation")
        .agg(
            ankomster=("numb_guests", "sum"),
            overnatninger=("overnatninger", "sum")
        )
        .reset_index()
    )

    hovedlande = ["DK", "D", "S", "N", "NL"]

    stats["nation"] = stats["nation"].fillna("").str.upper()

    stats["gruppe"] = stats["nation"].apply(
        lambda x: x if x in hovedlande else "ANDRE"
    )

    rapport = (
        stats.groupby("gruppe")
        .agg({
            "ankomster": "sum",
            "overnatninger": "sum"
        })
        .reset_index()
    )

    st.success("Forbindelse OK")

except Exception as e:
    st.error(f"Fejl: {e}")

st.subheader("Rapport til Danmarks Statistik")
st.caption(
    "Annullerede bookinger (web = cansl) er filtreret fra i alle tal på siden."
)
st.metric(
    "Solgte værelsesnætter i 2026",
    f"{sold_room_nights_2026:,}".replace(",", "."),
)
st.dataframe(rapport)

st.subheader("Fordeling af solgte værelsesnætter i 2026")

# Bookingkanaler

# Brug samme år og samme definition som totalen ovenfor. Landefilteret til
# Danmarks Statistik må ikke fjerne bookinger uden landekode herfra.
kanal_seasons = pd.to_numeric(bookings_df["season"], errors="coerce")
kanal_df = bookings_df[kanal_seasons.eq(2026)].copy()

kanal_df["kanal"] = (
    kanal_df["web"].fillna("").astype(str).str.upper().str.strip()
)

kanal_df["kanal"] = kanal_df["kanal"].apply(
    lambda x: "Booking.com" if x == "BC" else "Egne bookinger"
)

kanal_stats = (
    kanal_df.groupby("kanal")
    .agg(
        solgte_værelsesnætter=("nights", "sum")
    )
    .reset_index()
)

st.write(kanal_stats)
fig = px.pie(
    kanal_stats,
    names="kanal",
    values="solgte_værelsesnætter",
    title="Andel af solgte værelsesnætter fra Booking.com i 2026"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Booking pace")

response = (
    supabase.table("bookin_pace")
    .select("*")
    .execute()
)

pace_df = pd.DataFrame(response.data)
if pace_df.empty:
    st.info("Der er ingen booking pace-data at vise.")
else:
    pace_df["week_number"] = pd.to_numeric(
        pace_df["week_number"], errors="coerce"
    )
    pace_df["season_year"] = pd.to_numeric(
        pace_df["season_year"], errors="coerce"
    )
    pace_df["sold_nights"] = pd.to_numeric(
        pace_df["sold_nights"], errors="coerce"
    )
    pace_df = pace_df.dropna(
        subset=["week_number", "season_year", "sold_nights"]
    )

    # Supabase garanterer ikke rækkefølgen uden en eksplicit sortering.
    # Behold den senest indsatte række, hvis samme sæson/uge forekommer flere gange.
    if "id" in pace_df.columns:
        pace_df["id"] = pd.to_numeric(pace_df["id"], errors="coerce")
        pace_df = pace_df.sort_values("id", na_position="first")
    pace_df = pace_df.drop_duplicates(
        subset=["season_year", "week_number"], keep="last"
    )
    pace_df = pace_df.sort_values(["season_year", "week_number"])
    pace_df["season_year"] = pace_df["season_year"].astype(int).astype(str)

    fig = px.line(
        pace_df,
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

# st.subheader(" Omsætning inkl. moms")
#
# historik_df = pd.DataFrame({
#     "year": [2024, 2025],
#     "maj": [86980, 78599],
#     "juni": [143719, 121385],
#     "juli": [151706, 146531],
#     "aug": [146913, 159691],
#     "sep": [107810, 104591]
# })
# df["checkin_date"] = pd.to_datetime(df["checkin_date"])
#
# df["year"] = df["checkout_date"].dt.year
# df["month"] = df["checkout_date"].dt.month
#
# df["pris"] = (
#     df["pris"]
#     .astype(str)
#     .str.replace(",", ".", regex=False)
# )
#
# df["pris"] = pd.to_numeric(
#     df["pris"],
#     errors="coerce"
# )
# oms_2026 = (
#     df[df["year"] == 2026]
#     .groupby("month")
#     .agg(
#         revenue=("pris", "sum")
#     )
# )
# df["month"] = df["checkout_date"].dt.month
#
# ny_række = pd.DataFrame({
#     "year": [2026],
#     "maj": [oms_2026.loc[5, "revenue"] if 5 in oms_2026.index else 0],
#     "juni": [oms_2026.loc[6, "revenue"] if 6 in oms_2026.index else 0],
#     "juli": [oms_2026.loc[7, "revenue"] if 7 in oms_2026.index else 0],
#     "aug": [oms_2026.loc[8, "revenue"] if 8 in oms_2026.index else 0],
#     "sep": [oms_2026.loc[9, "revenue"] if 9 in oms_2026.index else 0],
# })
# historik_df = pd.concat(
#     [historik_df, ny_række],
#     ignore_index=True
# )
# #st.subheader("Omsætning pr. måned med moms")
#
# st.dataframe(historik_df)
# historik_long = historik_df.melt(
#     id_vars="year",
#     var_name="month",
#     value_name="revenue"
# )
# historik_long["year"] = historik_long["year"].astype(str)
#
# fig = px.bar(
#     historik_long,
#     x="month",
#     y="revenue",
#     color="year",
#     barmode="group",  # side om side
#     title="Omsætning pr. måned inkl moms"
# )
# st.write(df["pris"].sum())
# #st.write(df["pris"].describe())
# st.write(
#     df.groupby("month")
#       .agg(
#           bookinger=("pris", "count"),
#           omsaetning=("pris", "sum")
#       )
# )
# st.plotly_chart(fig, use_container_width=True)

st.subheader("Morgenmadsomsætning")
st.write("Morgenmadsomsætning er prebooked morgenmad fratrukket rabat og moms")

selected_season = st.selectbox(
    "Sæson",
    [2026, 2027],
    index=0
)

breakfast_price_result = (
    supabase.table("high_season")
    .select("pris_morgenmad")
    .eq("season", selected_season)
    .limit(1)
    .execute()
)
breakfast_price_rows = breakfast_price_result.data or []
breakfast_price = pd.to_numeric(
    breakfast_price_rows[0].get("pris_morgenmad") if breakfast_price_rows else 0,
    errors="coerce",
)
breakfast_price = 0 if pd.isna(breakfast_price) else float(breakfast_price)

# Morgenmadsomsætning: personer med BF=Y gange nætter og sæsonpris.
booking_seasons = pd.to_numeric(bookings_df["season"], errors="coerce")
breakfast_bookings = bookings_df[
    booking_seasons.eq(selected_season)
    & bookings_df["morgenmad"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
    .eq("Y")
].copy()
breakfast_guests = pd.to_numeric(
    breakfast_bookings["numb_guests"], errors="coerce"
).fillna(0)
breakfast_nights = pd.to_numeric(
    breakfast_bookings["nights"], errors="coerce"
).fillna(0).clip(lower=0)
breakfast_bookings["numb_guests"] = breakfast_guests
breakfast_bookings["nights"] = breakfast_nights

# Rabat er historisk gemt som tekst eller decimaltal. Både 0,10, 10 og 10% tolkes som 10%.
discount_text = (
    breakfast_bookings["rabat"]
    .fillna("0")
    .astype(str)
    .str.strip()
    .str.replace(",", ".", regex=False)
    .str.extract(r"(-?\d+(?:\.\d+)?)", expand=False)
)
discount_rate = pd.to_numeric(discount_text, errors="coerce").fillna(0)
discount_rate = discount_rate.where(discount_rate.abs() <= 1, discount_rate / 100)
discount_rate = discount_rate.clip(lower=0, upper=1)

# Kun egne webbookinger får rabat. FM-værdien er et tillæg, ikke en rabat.
booking_channel = (
    breakfast_bookings["web"].fillna("").astype(str).str.strip().str.lower()
)
breakfast_bookings["discount_rate"] = discount_rate.where(
    booking_channel.eq("web"), 0
)

# En række pr. overnatningsdato giver korrekt fordeling ved månedsskifte.
breakfast_bookings["breakfast_date"] = breakfast_bookings.apply(
    lambda row: pd.date_range(
        start=row["checkin_date"],
        periods=int(row["nights"]),
        freq="D",
    ) if pd.notna(row["checkin_date"]) and row["nights"] > 0 else [],
    axis=1,
)
breakfast_by_night = breakfast_bookings.explode("breakfast_date")
breakfast_by_night = breakfast_by_night.dropna(subset=["breakfast_date"])
breakfast_by_night["breakfast_date"] = pd.to_datetime(
    breakfast_by_night["breakfast_date"], errors="coerce"
)
breakfast_by_night["gross_revenue"] = (
    breakfast_by_night["numb_guests"] * breakfast_price
)
breakfast_by_night["net_revenue"] = (
    breakfast_by_night["gross_revenue"]
    * (1 - breakfast_by_night["discount_rate"])
    / 1.25
)

month_names = {
    1: "Januar", 2: "Februar", 3: "Marts", 4: "April",
    5: "Maj", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "December",
}
if breakfast_by_night.empty:
    breakfast_monthly = pd.DataFrame(
        columns=["Måned", "Morgenmåltider", "Nettoomsætning"]
    )
else:
    breakfast_by_night["month"] = breakfast_by_night["breakfast_date"].dt.month
    breakfast_monthly = (
        breakfast_by_night.groupby("month", as_index=False)
        .agg(
            Morgenmåltider=("numb_guests", "sum"),
            Nettoomsætning=("net_revenue", "sum"),
        )
        .sort_values("month")
    )
    breakfast_monthly["Måned"] = breakfast_monthly["month"].map(month_names)
    breakfast_monthly = breakfast_monthly[
        ["Måned", "Morgenmåltider", "Nettoomsætning"]
    ]

breakfast_servings = breakfast_monthly["Morgenmåltider"].sum()
breakfast_revenue = breakfast_monthly["Nettoomsætning"].sum()

st.metric(
    "Omsætning",
    f"{breakfast_revenue:,.2f} kr".replace(",", "X").replace(".", ",").replace("X", "."),
    help=(
        f"{breakfast_servings:,.0f} morgenmåltider til {breakfast_price:,.2f} kr, "
        "efter rabat og ekskl. 25% moms"
        .replace(",", "X").replace(".", ",").replace("X", ".")
    ),
)
st.dataframe(
    breakfast_monthly.style.format({
        "Morgenmåltider": "{:,.0f}",
        "Nettoomsætning": "{:,.2f} kr",
    }),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Sæsonstatistik")

df_stats = bookings_df.copy()

# Datoformat
df_stats["checkin_date"] = pd.to_datetime(df_stats["checkin_date"], errors="coerce")
df_stats["checkout_date"] = pd.to_datetime(df_stats["checkout_date"], errors="coerce")

# Fjern annullerede bookinger
df_stats = exclude_cancelled_bookings(df_stats)
# Kun valgt sæson
df_stats = df_stats[
    df_stats["season"] == int(selected_season)
]

# Beregn bookinglængde i nætter
df_stats["booking_length"] = (
    df_stats["checkout_date"] - df_stats["checkin_date"]
).dt.days

# Fjern fejl / tomme datoer
df_stats = df_stats[
    df_stats["booking_length"].notna()
]

df_stats = df_stats[
    df_stats["booking_length"] > 0
]

# Måned ud fra check-in dato
st.subheader("Indcheckninger fordelt på ugedage")

if df_stats.empty:
    st.info("Der er ingen aktive bookinger med gyldige datoer i den valgte sæson.")
else:
    period_start = df_stats["checkin_date"].min().date()
    period_end = df_stats["checkin_date"].max().date()
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
        checkins = df_stats.dropna(subset=["checkin_date"]).copy()
        if "booking_number" in checkins.columns:
            checkins = checkins.drop_duplicates(
                subset=["booking_number", "checkin_date"]
            )
        checkins["checkin_day"] = checkins["checkin_date"].dt.date

        weekday_order = [
            "Mandag", "Tirsdag", "Onsdag", "Torsdag",
            "Fredag", "Lørdag", "Søndag",
        ]

        def weekday_distribution(period_df):
            counts = (
                period_df["checkin_date"].dt.dayofweek
                .value_counts()
                .reindex(range(7), fill_value=0)
            )
            total = int(counts.sum())
            percentages = counts / total * 100 if total else counts.astype(float)
            return pd.DataFrame({
                "Ugedag": weekday_order,
                "Antal": counts.to_numpy(),
                "Procent": percentages.to_numpy(),
            }), total

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

df_stats["month"] = df_stats["checkin_date"].dt.month
df_stats["month_name"] = df_stats["checkin_date"].dt.strftime("%b")

st.subheader("Gennemsnitlig bookinglængde pr. måned")

avg_length = (
    df_stats
    .groupby(["month", "month_name"])["booking_length"]
    .mean()
    .reset_index()
    .sort_values("month")
)

fig = px.bar(
    avg_length,
    x="month_name",
    y="booking_length",
    text=avg_length["booking_length"].round(1),
    labels={
        "month_name": "Måned",
        "booking_length": "Gennemsnitlig bookinglængde"
    },
    title="Gennemsnitlig bookinglængde pr. måned"
)

fig.update_traces(
    textposition="outside"
)

fig.update_layout(
    yaxis_title="Nætter",
    xaxis_title="Måned"
)

st.plotly_chart(fig, use_container_width=True)
