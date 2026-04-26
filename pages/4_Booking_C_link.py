import streamlit as st
from auth import require_login

st.set_page_config(page_title="link", layout="wide")
require_login()

st.link_button("Booking_com", "https://account.booking.com/sign-in?op_token=EgVvYXV0aCLvAgoUNlo3Mm9IT2QzNk5uN3prM3BpcmgSCWF1dGhvcml6ZRoaaHR0cHM6Ly9hZG1pbi5ib29raW5nLmNvbS8q9gF7InBhZ2UiOiIvaG90ZWwvaG90ZWxhZG1pbi9leHRyYW5ldF9uZy9tYW5hZ2UvYm9va2luZy5odG1sP3Jlc19pZD0xNTQzNDc3NTg1JmhvdGVsX2lkPTMyODkyMCZsYW5nPWRhJmZyb21fY29uZmlybWF0aW9uX2VtYWlsPTEmX2U9MTUzNDg2NjgzMyZfcz1qZmZDbzlGZFlSNHd4K3NWZTZaWk8vOGNaZ2M2ZXlZUW1aRnFsd01pcmRRIiwiYXV0aF9hdHRlbXB0X2lkIjoiODViMDc1MTItNmExZi00NDlhLTgwNjAtYjg2OGJhZDRiMzEzIn0yK2xFX3lqaUZwOHFFV3JoRG82V3JTbEV5U2xDdXQ5REwyNFNQaXpLUkdsWms6BFMyNTZCBGNvZGUqEzCT2or4m7QoOgBCAFjPz7ec3DM")
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               #)https://account.booking.com")