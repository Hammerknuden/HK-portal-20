"""Execute the actual level-2 UI section with fake UI/database adapters.

No database or server is started. These are integration checks, not visual QA.
"""
import ast
from pathlib import Path
from unittest.mock import patch
import unittest

import pandas as pd

from test_level2_optimizer import booking, optimizer, FixedDate, preview, workflow
from modules.optimizer_state import booking_signature, invalidate_analysis


class FakeUI:
    def __init__(self, clicked=True):
        self.session_state = {}
        self.clicked = clicked
        self.messages = []
        self.tables = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def button(self, label, **kwargs):
        if label == "Vælg denne løsning":
            return False
        if label != "🔍 Undersøg optimeringsmuligheder":
            raise AssertionError("Save must not appear before selecting and previewing.")
        return self.clicked and not kwargs.get("disabled", False)

    def dataframe(self, data, **kwargs):
        self.tables.append(data.copy())

    def __getattr__(self, name):
        if name not in {"subheader", "caption", "spinner", "error", "info", "container",
                        "markdown", "write", "warning", "success", "expander"}:
            raise AttributeError(name)
        def emit(*args, **kwargs):
            self.messages.append((name, args))
            return self
        return emit


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.ranges = []

    def table(self, name):
        assert name == "hk_dtb"
        return self

    def select(self, columns):
        return self

    def order(self, column):
        assert column == "id"
        return self

    def range(self, start, end):
        self.ranges.append((start, end))
        self.data = self.rows[start:end+1]
        return self

    def execute(self):
        return self


class OptimizerViewTests(unittest.TestCase):
    def run_view(self, ui, database):
        source = (Path(__file__).parents[1] / "pages" / "6_timeline.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        start = next(i for i, node in enumerate(tree.body)
                     if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Attribute)
                     and node.value.func.attr == "subheader"
                     and node.value.args and isinstance(node.value.args[0], ast.Constant)
                     and node.value.args[0].value == "Niveau 2 optimering")
        section = ast.Module(body=tree.body[start:], type_ignores=[])
        scope = {"st": ui, "pd": pd, "supabase": database,
                 "selected_season": 2026, "analyze_improvements": optimizer.analyze_improvements,
                 "select_plan": preview.select_plan, "clear_selection": workflow.clear_selection,
                 "booking_today": FixedDate.today, "booking_signature": booking_signature,
                 "invalidate_analysis": invalidate_analysis,
                 "render_selected_solution": workflow.render_selected_solution,
                 "uses_supabase_auth": lambda: False}
        with patch.object(optimizer, "date", FixedDate):
            exec(compile(section, "optimizer_ui", "exec"), scope)
        return scope

    def test_all_moves_are_displayed_without_database_writes(self):
        ui = FakeUI()
        self.run_view(ui, FakeDatabase([booking(1, 7), booking(2, 1)]))
        result = ui.session_state["optimizer_suggestions"]
        options = result["recommendations"][0]["options"]
        self.assertEqual(len(ui.tables), len(options))
        for table, plan in zip(ui.tables, options):
            self.assertEqual(table["Database-ID"].tolist(), [m["id"] for m in plan["moves"]])
            self.assertEqual(table["Til værelse"].tolist(), [m["to_room"] for m in plan["moves"]])
        self.assertFalse(any(name == "error" for name, _ in ui.messages))

    def test_loader_paginates_and_keeps_other_seasons(self):
        ui = FakeUI(clicked=False)
        rows = [{**booking(i, 6), "season": 2027} for i in range(1001)]
        database = FakeDatabase(rows)
        scope = self.run_view(ui, database)
        result = scope["load_optimizer_bookings"]()
        self.assertEqual(len(result), 1001)
        self.assertEqual(database.ranges, [(0, 999), (1000, 1999)])
        self.assertTrue(result["season"].eq(2027).all())

    def test_old_suggestions_are_discarded(self):
        ui = FakeUI(clicked=False)
        ui.session_state["optimizer_suggestions"] = {"recommendations": [{"status": "ready"}]}
        self.run_view(ui, FakeDatabase([]))
        self.assertNotIn("optimizer_suggestions", ui.session_state)
        self.assertFalse(ui.tables)

    def test_failed_fetch_does_not_keep_old_suggestions(self):
        ui = FakeUI()
        ui.session_state["optimizer_suggestions"] = {"schema_version": 2}
        database = FakeDatabase([])
        with patch.object(database, "execute", side_effect=RuntimeError("offline")):
            self.run_view(ui, database)
        self.assertNotIn("optimizer_suggestions", ui.session_state)
        self.assertTrue(any(name == "error" for name, _ in ui.messages))

    def test_returning_after_deletion_clears_analysis(self):
        ui = FakeUI()
        self.run_view(ui, FakeDatabase([booking(1, 7), booking(2, 1)]))
        ui.clicked = False
        ui.tables.clear()
        self.run_view(ui, FakeDatabase([booking(2, 1)]))
        self.assertNotIn("optimizer_suggestions", ui.session_state)
        self.assertEqual(ui.tables, [])

    def test_unchanged_data_keeps_analysis_when_returning(self):
        ui = FakeUI()
        rows = [booking(1, 7), booking(2, 1)]
        self.run_view(ui, FakeDatabase(rows))
        original = ui.session_state["optimizer_suggestions"]
        ui.clicked = False
        self.run_view(ui, FakeDatabase(list(reversed(rows))))
        self.assertIs(ui.session_state["optimizer_suggestions"], original)

    def test_changed_lock_or_date_clears_selection_and_preview(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 1)])
        signature = booking_signature(rows, 2026, FixedDate.today())
        for column, value in (("movable", False), ("room_number", 5),
                              ("checkout_date", pd.Timestamp("2026-09-25"))):
            changed = rows.copy()
            changed.loc[changed["id"] == 2, column] = value
            state = {"optimizer_suggestions": {"data_signature": signature},
                     "optimizer_choice": {"plan": {}}, "optimizer_preview": {"save_pending": False}}
            self.assertTrue(invalidate_analysis(state, booking_signature(changed, 2026, FixedDate.today())))
            self.assertEqual(state, {})
        state = {"optimizer_suggestions": {"data_signature": signature}}
        self.assertTrue(invalidate_analysis(state, booking_signature(rows, 2026, pd.Timestamp("2026-09-16").date())))

    def test_uncertain_save_survives_changed_data(self):
        state = {"optimizer_suggestions": {"data_signature": "old"},
                 "optimizer_choice": {"request_id": "keep"},
                 "optimizer_preview": {"save_pending": True, "request_id": "keep"}}
        self.assertFalse(invalidate_analysis(state, "new"))
        self.assertEqual(state["optimizer_preview"]["request_id"], "keep")


if __name__ == "__main__":
    unittest.main()
