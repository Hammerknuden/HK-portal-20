import pandas as pd


PRICE_FIELDS = {
    "enk_low": "Enkelt lavsæson",
    "enk_high": "Enkelt højsæson",
    "dobb_low": "Dobbelt lavsæson",
    "dobb_high": "Dobbelt højsæson",
    "pris_morgenmad": "Morgenmad",
}


def percentage_change(current, previous):
    """Return year-over-year percentage change, or None without a baseline."""
    if previous is None or pd.isna(previous) or float(previous) == 0:
        return None
    if current is None or pd.isna(current):
        return None
    return (float(current) / float(previous) - 1) * 100


def build_price_development(price_rows, draft_season=None, draft_prices=None):
    """Build a price and year-over-year development table."""
    rows = []
    previous = None

    for source in sorted(price_rows, key=lambda row: int(row["season"])):
        season = int(source["season"])
        values = {field: float(source[field]) for field in PRICE_FIELDS}
        if season == draft_season and draft_prices:
            values.update(
                {field: float(draft_prices[field]) for field in PRICE_FIELDS}
            )

        row = {"År": season}
        for field, label in PRICE_FIELDS.items():
            row[label] = values[field]
            row[f"{label} ændring"] = (
                percentage_change(values[field], previous[field])
                if previous is not None
                else None
            )
        rows.append(row)
        previous = values

    return pd.DataFrame(rows)
