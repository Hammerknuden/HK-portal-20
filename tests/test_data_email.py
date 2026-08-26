import unittest

import pandas as pd

from config.data_email import add_data


class DataEmailExcelTests(unittest.TestCase):
    def test_family_name_is_written_to_excel(self):
        excel_buffer = add_data(
            booking_number="42",
            name="Anna",
            family_name="Jensen",
            formatted_pristotal="1000,00",
        )

        exported = pd.read_excel(excel_buffer, sheet_name="book")

        self.assertIn("familie_navn", exported.columns)
        self.assertEqual(exported.loc[0, "familie_navn"], "Jensen")


if __name__ == "__main__":
    unittest.main()
