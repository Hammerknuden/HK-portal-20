import streamlit as st
from auth import require_login

st.set_page_config(page_title="link", layout="wide")
require_login()

st.link_button("Booking_com", "https://account.booking.com")
st.link_button("Booking com fj", "https://admin.booking.com/?page=%2Fhotel%2Fhoteladmin%2"
                "Fextranet_ng%2Fmanage%2Fbooking.html%3Fres_id%3D1543477585%26hotel_id%3D328920%26"
                "lang%3Dda%26from_confirmation_email%3D1%26_e%3D1534866833%26_s%3DjffCo9FdYR4wx%2BsVe6ZZO%2"
                "F8cZgc6eyYQmZFqlwMirdQ&message=ERR100&lang=da")
st.link_button("Mobil pay", "https://portal.vippsmobilepay.com/login")
st.link_button("Zettle", "https://login.zettle.com/login?username=bonnevie%40mail.dk")
st.link_button("Danske Bank", "https://district.danskebank.dk/Logon#/") #https://shared-logon.danskebank.com/logon/default/index.html?clientId=District-DK")
st.link_button("Dinero", "https://connect.visma.com/?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_"
                         "id%3Ddinero%26redirect_uri%3Dhttps%253A%252F%252Fapp."
                         "dinero.dk%252Fsignin-oidc%26response_type%3Dcode%2520id_token%26scope%3Dopenid%2520profile%2520email%2520roles%26response"
                         "_mode%3Dform_post%26nonce%3D639196062013793028.MDJkNTI3ZDgtZDdmOC00NTc3LTk5MTktZjgxOWEw"
                         "ZjU3MGM1NTlhNDE1ODEtZGI3Yi00NWIwLTkwYzctZDBjZDNhOGYwMDFm%26state%3DCfDJ8IiuaGEVxBVJjTO5tUpz9"
                         "4Ljv87h2ZyqswVNknyehx1gRzAZUdRBUwvdxSxjc1IlSQsQxUew4bABCDz3bjI2i7HWahO6vKSLWG8FgeqOCyF8Su1eODpvyoNl-"
                         "EltXA2YdzKWBlxmpE49WzS0PLBuJFvS1f1OFcpi31PzivvpfAEiGDI236Ja_oMXjmdGxx42jlZhSqclvC2GqqRnV_L_"
                         "smUXWg3_lko5UO19HDVEbGOkGNEPFrK9BW7UeGhrGV6SgfWUwsmzn3n8YYLHrY1Wr2gJVT3H52e8hJoWlQvYYkNVg"
                         "GY56z1YnmDorJaDPuiXZw%26x-client-SKU%3DID_NET9_0%26x-client-ver%3D8.0.1.0")
