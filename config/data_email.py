import smtplib
from email.message import EmailMessage
import ssl
from email.utils import make_msgid
from pathlib import Path
from io import BytesIO
import pandas as pd
import openpyxl


port = 587
smtp_server = 'send.one.com'
Subject = "HK reservations data"
sender_email = 'reservation@hammerknuden.dk'
admin_email = 'reservation@hammerknuden.dk'
logo_path = Path("logo2.jpg")


def add_data(year=None, booking_number=None, name=None, checkin_date=None, checkout_date=None, now=None,
             nationalitet=None, web=None, ankomst=None, seng=None, rabat_a=None, num_rooms=None,
             num_guests=None, email_address=None, telefon=None, spouse=None, single_room=None,
             BF=None, formatted_pristotal=None, known=None, comments=None):

    book_data = {
        'book nr': [booking_number],
        'navn': [name],
        'Checkin': [checkin_date],
        'checkout': [checkout_date],
        'booking dato': [now],
        'nation': [nationalitet],
        'web': [web],
        'ankomst': [ankomst],
        'bed': [seng],
        'rabat': [rabat_a],
        'antal værelser': [num_rooms],
        'nr gæst': [num_guests],
        'Email': [email_address],
        'telefon': [telefon],
        'Spouse': [spouse],
        'enkelt': [single_room],
        'morgenmad': [BF],
        'pris ialt': [formatted_pristotal],
        'known': [known],
        'Comments': [comments]
    }
    df1 = pd.DataFrame(book_data)

    df1['Checkin'] = pd.to_datetime(df1['Checkin'], errors='coerce')
    df1['checkout'] = pd.to_datetime(df1['checkout'], errors='coerce')
    df1['booking dato'] = pd.to_datetime(df1['booking dato'], errors='coerce')
    df1['book nr'] = df1['book nr'].str.replace(',', '.').astype(float)
    df1['pris ialt'] = df1['pris ialt'].str.replace(',', '.').astype(float)
    #df1['rabat'] = df1['rabat'].str.replace(',', '.').astype(float)
    excel_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter',  datetime_format="dd-mm-yy") as writer:
        df1.to_excel(writer, sheet_name='book', index=False)

    excel_buffer.seek(0)  # VIGTIGT!

    return excel_buffer


def send_email(confirmation_password, email):
    context = ssl.create_default_context()
    # Send the message via local SMTP server.
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(admin_email, confirmation_password)
        server.send_message(email)


def data_email_html_template(
        logo_cid,
        booking_number,
        name,
        checkin_date,
        checkout_date,
        now,
        nationalitet,
        web,
        ankomst,
        seng,
        rabat_a,
        num_rooms,
        num_guests,
        email_address,
        telefon,
        formatted_pristotal):

    return f"""
    <html>
        <body style="font-family: Arial, sans-serif;">

            <hr>
            <h2>Reservation Data</h2>
            <hr>

            <img src="cid:{logo_cid}" alt="logo" width="300"/>

            <p>
                Data mail for reservation <br>
                Booknr: {booking_number} <br>
                Navn:<b>{name}</b><br>
                Fra Dato:**{checkin_date}**, Til Dato**{checkout_date}**<br><br>
                Booking dato {now}, <br>
                Nationalitet** {nationalitet} **<br>
                Booking metode **{web}** <br>
                Senge type {seng} <br> 
                Rabat ved booking {rabat_a};
            </p>

            <p>
                Antal værelser:<b>{num_rooms}</b> antal gæster <b>{num_guests}</b><br>
            </p>

            <p>
                <b>Kontakt oplysninger:</b><br>
                Email: {email_address}; {telefon}<br>
            </p>
            <p>
                <b>Total pris:</b> {formatted_pristotal} kr
            </p>

        </body>
    </html>
    """


def send_data_email(to_addr_1, confirmation_password, booking_number, name, checkin_date, checkout_date, num_rooms,
                    now, nationalitet, web, ankomst, seng, rabat_a, num_guests, email_address, telefon,
                    formatted_pristotal, excel_buffer):

    logo_cid = make_msgid()
    html_content = data_email_html_template(logo_cid[1:-1], booking_number, name, checkin_date, checkout_date,
                                            now, nationalitet, web, ankomst, seng, rabat_a, num_rooms, num_guests,
                                            email_address, telefon, formatted_pristotal)

    # construct email
    email = EmailMessage()

    email['Subject'] = Subject + f" #{booking_number}"
    email['From'] = sender_email
    email['To'] = to_addr_1
    email.set_content("Email client does not support html content")
    email.add_alternative(html_content, subtype='html')
    with (open(logo_path, 'rb') as img):
        email.get_payload()[1].add_related(img.read(), maintype='image', subtype='jpeg', cid=logo_cid)

    excel_buffer.seek(0)

    email.add_attachment(
        excel_buffer.read(),
        maintype='application',
        subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=f'booking_{booking_number}.xlsx')

    send_email(confirmation_password, email)