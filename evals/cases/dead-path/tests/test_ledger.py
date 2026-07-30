import unittest

from ledger import app
from ledger.controls import RejectedEntry


def payload(ref="R-1", amount=250, currency="EUR"):
    return {"ref": ref, "amount": amount, "currency": currency}


class TestIngest(unittest.TestCase):
    def test_entry_is_built_from_payload(self):
        entry = app.ingest(payload())
        self.assertEqual(entry["ref"], "R-1")
        self.assertEqual(entry["amount"], 250)

    def test_unsupported_currency_is_rejected(self):
        with self.assertRaises(RejectedEntry):
            app.ingest(payload(currency="XYZ"))


class TestExport(unittest.TestCase):
    def test_entries_render_with_the_configured_exporter(self):
        out = app.export([app.ingest(payload())])
        self.assertIn("ref,amount,currency", out)
        self.assertIn("R-1,250,EUR", out)

    def test_export_of_no_entries_is_a_header_only_document(self):
        self.assertEqual(app.export([]), "ref,amount,currency")


if __name__ == "__main__":
    unittest.main()
