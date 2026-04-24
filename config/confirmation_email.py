import smtplib
from email.message import EmailMessage
import ssl
from email.utils import make_msgid
from pathlib import Path
from datetime import datetime


port = 587 #587
smtp_server = 'send.one.com'  #'asmtp.yousee.dk'
Subject = "Hammerknuden Reservation"
sender_email = 'reservation@hammerknuden.dk' #'Hkreservation@mail.dk'
admin_email = 'reservation@hammerknuden.dk' #'Hkreservation@mail.dk'  #'reservation@hammerknuden.dk'
logo_path = Path("logo2.jpg")


def send_email(confirmation_password, email):
    context = ssl.create_default_context()
    # Send the message via local SMTP server.
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(admin_email, confirmation_password)
        server.send_message(email)


def danish_email_html_template(logo_cid, name, num_rooms, num_guests, booking_number, checkin_date, checkout_date,
                               text_bf, formatted_prismed, text_web, formatted_justering, formatted_pristotal, text_ank,
                               text_bed, text_free, email_address, telefon):

    return f"""<html>        <html style="display: table; margin: auto;">
        <head>
            <meta charset="UTF-8" />
            <title>Reservationsformular</title>
            <script defer src="https://pyscript.net/alpha/pyscript.js"></script>
        </head>
    
        <body style="display: table-cell; vertical-align: left;">
            <hr>
            <h1> ********************* </h1> 
            <h1>   Reservation</h1> 
            <h1> ********************* </h1>
             
            <img src ="cid:{logo_cid}" alt=logo width="300"/>
            </p>
            <p>
            Der er idag foretaget følgende reservation for <b>{name}</b> 
            </p>
            <p>Der er reserveret {num_rooms} Dobbelt værelse med bad, kitchenette og terrasse til ialt 
            {num_guests} personer. </p>
            <p>
            med booking nummer              <b>{booking_number}</b> <!-- formattering foregår også med tags  -->
            <hr>
            <p>Indcheck er den<span style="padding-left:3em"><b> {checkin_date}</b></span></p>
            <p>Udcheck den<span style="padding-left:4em"><b> {checkout_date}</b></span></p>
            <hr>
            <p>Indcheck er efter kl. 14:30 på indcheckningsdagen og udcheck før kl. 10:00, ellers efter aftale</p>
            <hr>
            <table>
                <tr>
                    <td>{text_bf}</td>
                    <td style="text-align:right;"> -- </td>
                </tr>
                <tr>
                    <td>Prisen på opholdet er</td>
                    <td style="text-align:right;">{formatted_prismed} kr </td>
                </tr>
                <tr>
                    <td>{text_web}</td>
                    <td style="text-align:right;">{formatted_justering} kr </td>
                </tr>
                <tr>
                    <td>Endelig pris afregnes under opholdet.</td>
                    <td style="text-align:right;">{formatted_pristotal} kr </td>
                </tr>
                <hr>
                <tr>
                    <td> Jeres/Din kontakt information email: {email_address} telefon : {telefon} </td>
                </tr>
            </table>
            <hr>
            <p> GDPR; Hammerknuden gemmer navn, adresse, email og telefon nummer som en del af den obligatoriske gæste 
            registrering, oplysningerne anvendes herudover til statistisk brug, hvis dette ikke er acceptabelt 
            skriv en email til admin@hammerknuden.dk </p>
            <p> {text_ank} </p
            <p> {text_bed} </p>
            <p> {text_free} </p>
            <hr>
            </p>
            <p align="center"><strong>HAMMERKNUDEN SOMMERPENSION</strong><br>
            Hammershusvej 74 - 3770 Allinge<br>
            mail@hammerknuden.dk - +45 56481750  (call only)<br>
            Mobil pay - 133565 or Danske Bank reg 4720 kt 4720758679</align></p></p>
        </body>
        </html>
    """


def send_danish_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests,
                                   booking_number, checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                   formatted_justering, formatted_pristotal, text_ank, text_bed, text_free, email_address,
                                   telefon):

    logo_cid = make_msgid()
    html_content = danish_email_html_template(logo_cid[1:-1], name, num_rooms, num_guests, booking_number,
                                              checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                              formatted_justering, formatted_pristotal, text_ank, text_bed, text_free,
                                              email_address, telefon)
    # construct email
    email = EmailMessage()

    email['Subject'] = Subject + f" #{booking_number}"
    email['From'] = sender_email
    email['To'] = to_addr
    email.set_content("Email client does not support html content")
    email.add_alternative(html_content, subtype='html')

    with open(logo_path, 'rb') as img:
        email.get_payload()[0].add_related(img.read(), 'image', 'jpeg', cid=logo_cid)

    send_email(confirmation_password, email)


def english_email_html_template(logo_cid, name, num_rooms, num_guests, booking_number, checkin_date, checkout_date,
                                text_bf, formatted_prismed, text_web, formatted_justering, formatted_pristotal,
                                text_ank, text_bed, text_free, email_address, telefon):

    return f"""<html>        <html style="display: table; margin: auto;">
        <head>
            <meta charset="UTF-8" />
            <title>Reservationsformular</title>
            <script defer src="https://pyscript.net/alpha/pyscript.js"></script>
        </head>

        <body style="display: table-cell; vertical-align: left;">
            <hr>
            <h1> ********************* </h1> 
            <h1>   Reservation</h1> 
            <h1> ********************* </h1>

            <img src ="cid:{logo_cid}" alt=logo width="300"/>
            </p>
            <p>
            We have made the following reservation for <b>{name}</b>
            </p>
            <p>The reservation concerns {num_rooms} Double room including  bath, kitchenette og terresse 
            for a total number of {num_guests} guest(s) </p>
            <p>
            The booking reference number is              <b>{booking_number}</b> 
            <hr>
            <p>Inn check is on the <span style="padding-left:3em"><b>{checkin_date}</b></span></p>
            <p>Checkout is on the <span style="padding-left:3em"><b>{checkout_date}</b></span></p>
            <hr>
            <p>Check-in is after 14:30 on the day of check-in and check-out before 10:00, otherwise by appointment
            </p>
            <hr>
            <table>
                <tr>
                    <td>{text_bf}</td>
                    <td style="text-align:right;"> -- </td>
                </tr>
                <tr> 
                    <td>The price is.. </td>
                    <td style="text-align:right;">{formatted_prismed} kr </td>
                </tr>
                <tr>
                    <td>{text_web}..</td>
                    <td style="text-align:right;">{formatted_justering} kr </td>
                </tr>
                <tr>
                    <td>Total price to be settled during stay....</td>
                    <td style="text-align:right;">{formatted_pristotal} kr </td>
                </tr>
                <hr>
                <tr>
                    <td> Your Contact information email: {email_address}, Phone: {telefon} </td>
            </table>
            <hr>
            <p> GDPR; Hammerknuden stores name, address, email address and telephone number as part of the mandatory guest data registration 
            When registering, the data will also be used for statistical purposes, if this is not justifiable write an email to admin@hammerknuden.dk </p>
            <p> {text_ank} </p
            <p> {text_bed} </p>
            <p> {text_free} </p>
            <hr>
            </p>
            <p align="center"><strong>HAMMERKNUDEN SOMMERPENSION</strong><br>
            Hammershusvej 74 - 3770 Allinge<br>
            mail@hammerknuden.dk - +45 56481750  (call only)<br>
            Mobil pay - 133565 or Danske Bank reg 4720 kt 4720758679</align></p></p>
        </body>
        </html>
    """


def send_english_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests, booking_number,
                                    checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                    formatted_justering, formatted_pristotal, text_ank, text_bed, text_free,
                                    email_address, telefon):
    logo_cid = make_msgid()
    html_content = english_email_html_template(logo_cid[1:-1], name, num_rooms, num_guests, booking_number,
                                               checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                               formatted_justering, formatted_pristotal, text_ank, text_bed, text_free,
                                               email_address, telefon)
    # construct email
    email = EmailMessage()

    email['Subject'] = Subject + f" #{booking_number}"
    email['From'] = sender_email
    email['To'] = to_addr
    email.set_content("Email client does not support html content")
    email.add_alternative(html_content, subtype='html')

    with open(logo_path, 'rb') as img:
        email.get_payload()[0].add_related(img.read(), 'image', 'jpeg', cid=logo_cid)

    send_email(confirmation_password, email)


def german_email_html_template(logo_cid, name, num_rooms, num_guests, booking_number, checkin_date, checkout_date,
                               text_bf, formatted_prismed, text_web, formatted_justering, formatted_pristotal,
                               text_ank, text_bed, text_free, email_address, telefon):
    return f"""<html>        <html style="display: table; margin: auto;">
        <head>
            <meta charset="UTF-8" />
            <title>Reservationsformular</title>
            <script defer src="https://pyscript.net/alpha/pyscript.js"></script>
        </head>

        <body style="display: table-cell; vertical-align: left;">
            <hr>
            <h1> ********************* </h1> 
            <h1>   Reservation</h1> 
            <h1> ********************* </h1>

            <img src ="cid:{logo_cid}" alt=logo width="300"/>
            </p>
            <p>
            Heute wurde eine Reservierung im Namen von <b> {name} </b> vorgenommen 
            </p>
            <p>
            Die Reservierung gilt für {num_rooms} Doppelzimmer, Ed Bad, Kochnische und Terrasse für {num_guests} Gäste
            </p>
            <p>
            Buchungsnummer ist<span style="padding-left:3em"><b> {booking_number}</b> 
            <hr>
            <p>Reservierung ist von<span style="padding-left:3em"><b> {checkin_date}</b></span></p>
            <p>Bis<span style="padding-left:10em"><b> {checkout_date}</b></span></p>
            <hr>
            <p>Der Check-in erfolgt später 14:30 Uhr am Tag des Check-in und Check-out vorher 10:00 Uhr, ansonsten nach 
            Vereinbarung  </p>
            <hr>
            <table>
                <tr>
                    <td>{text_bf}</td>
                    <td style="text-align:right;"> -- </td>
                </tr>
                <tr>
                    <td>Der Preis für den Aufenthalt beträgt</td>
                    <td style="text-align:right;">{formatted_prismed} kr </td>
                </tr>
                <tr>
                    <td>{text_web}.</td>
                    <td style="text-align:right;">{formatted_justering} kr </td>
                </tr>
                <tr>
                    <td>Der Endpreis wird während des Aufenthalts abgerechnet.</td>
                    <td><span style=float:right>{formatted_pristotal} kr</span></td>
                </tr>
            <hr>
                <tr>
                    <td> Ihre Kontaktinformationen email: {email_address} Telefon; {telefon} </td>
                </tr>            
            </table>
            <hr>
            <p>DSGVO; Hammerknuden speichert Name, Adresse, E-Mail-Adresse und Telefonnummer als Teil der 
            obligatorischen Gastdaten Bei einer Registrierung werden die Daten auch für statistische Zwecke genutzt, 
            sofern dies nicht vertretbar ist schreibe eine E-Mail an admin@hammerknuden.dk </p>
            <p> {text_ank} </p
            <p> {text_bed} </p>
            <p> {text_free} </p>
            <hr>
            </p>
            <p align="center"><strong>HAMMERKNUDEN SOMMERPENSION</strong><br>
            Hammershusvej 74 - 3770 Allinge<br>
            mail@hammerknuden.dk - +45 56481750  (call only)<br>
            Mobil pay - 133565 or Danske Bank reg 4720 kt 4720758679</align></p></p>
        </body>
        </html>
    """


def send_german_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests,
                                   booking_number, checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                   formatted_justering, formatted_pristotal, text_ank, text_bed, text_free,
                                   email_address, telefon):
    logo_cid = make_msgid()
    html_content = german_email_html_template(logo_cid[1:-1], name, num_rooms, num_guests, booking_number,
                                              checkin_date, checkout_date, text_bf, formatted_prismed, text_web,
                                              formatted_justering, formatted_pristotal, text_ank, text_bed, text_free,
                                              email_address, telefon)
    # construct email
    email = EmailMessage()

    email['Subject'] = Subject + f" #{booking_number}"
    email['From'] = sender_email
    email['To'] = to_addr
    email.set_content("Email client does not support html content")
    email.add_alternative(html_content, subtype='html')

    with open(logo_path, 'rb') as img:
        email.get_payload()[0].add_related(img.read(), 'image', 'jpeg', cid=logo_cid)

    send_email(confirmation_password, email)

