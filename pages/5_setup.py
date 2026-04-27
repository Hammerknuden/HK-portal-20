import streamlit as st
from auth import require_login, require_admin
st.set_page_config(page_title="Setup", layout="wide")
require_login()
require_admin()

st.title("Setup ⚙️")

st.title("Pris modul setup")

st.write("priser 2026-2027-2028")
# Initialiser state første gang_

st.write("priser 2026-2027-2028")

from config.prices import DEFAULT_PRICES

if "prices" not in st.session_state:
    st.session_state.prices = DEFAULT_PRICES.copy()

st.session_state.prices["Sing-Room-HS-26"] = st.number_input(
    "Single room high season 2026",
    value=st.session_state.prices["Sing-Room-HS-26"]
)

if "prices" not in st.session_state:
    st.session_state.prices = {
        "Sing-Room-HS-26": 975,
        "Sing-Room-LS-26": 850,
        "Dobb-Room-HS-26": 1075,
        "Dobb-Room-LS-26": 950,
        "Breakfirst-26": 100,
        "Sing-Room-HS-27": 990,
        "Sing-Room-LS-27": 875,
        "Dobb-Room-HS-27": 1090,
        "Dobb-Room-LS-27": 980,
        "Breakfirst-27": 110,
    }

st.write("Rediger priser:")

# Opdater priser direkte i session_state
for produkt in st.session_state.prices:
    st.session_state.prices[produkt] = st.number_input(
        produkt,
        value=float(st.session_state.prices[produkt]),
        min_value=0.0,
        step=5.0,
        key=produkt
    )

# Vis aktuelle værdier
st.write("### Nuværende priser")
st.json(st.session_state.prices)
# Eksempel:
new_year = st.text_input("Tilføj nyt booking år")
if st.button("Gem"):
    st.success(f"{new_year} gemt!")
