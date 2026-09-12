"""Stable booking colours for the occupancy timeline."""

import colorsys
import hashlib
from decimal import Decimal, InvalidOperation


def booking_color(booking_number, booking_type, movable=True):
    """Use the channel's hue and a repeatable shade, with locked rows in red."""
    number = str(booking_number).strip()
    try:
        numeric = Decimal(number)
        if numeric.is_finite():
            number = format(numeric.normalize(), "f")
    except InvalidOperation:
        pass

    shade = int.from_bytes(hashlib.sha256(number.encode()).digest(), "big") % 8
    lightness = 0.655 - shade * 0.045
    channel = str(booking_type).strip().lower()
    locked = str(movable).strip().lower() in {"false", "0", "0.0"}
    hue = 0 if locked else {"web": 135, "bc": 212, "fm": 28}.get(channel)
    saturation = 0.68 if hue is not None else 0
    red, green, blue = colorsys.hls_to_rgb((hue or 0) / 360, lightness, saturation)
    return "#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in (red, green, blue)))
