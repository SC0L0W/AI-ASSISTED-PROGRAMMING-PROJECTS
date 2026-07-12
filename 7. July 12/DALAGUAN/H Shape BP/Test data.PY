"""
test_data.py

Lightweight tests for cb1_hshape_data.py: lookup normalization and all
20 CB1 H-shape records. Run with:

    python -m unittest test_data.py -v
"""

import unittest

from cb1_hshape_data import (
    CB1_H_SHAPE,
    normalize,
    find_record,
    get_record_by_mark,
    get_marks,
    bolt_offsets_mm,
    validate_records,
)

EXPECTED_MARKS = [
    "H153", "H253", "H304", "H356", "H405",
    "H202", "H254", "H305", "H357", "H452",
    "H203", "H255", "H352", "H402", "H552",
    "H205", "H302", "H355", "H404", "H602",
]


class TestNormalize(unittest.TestCase):
    def test_case_and_space_insensitive(self):
        self.assertEqual(normalize("h253"), "H253")
        self.assertEqual(normalize(" H 253 "), "H253")
        self.assertEqual(normalize("ub254x146x37"), "UB254X146X37")
        self.assertEqual(normalize("UB 254 x 146 x 37"), "UB254X146X37")

    def test_none_and_empty(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize(None), "")


class TestFindRecord(unittest.TestCase):
    def test_find_by_mark_exact(self):
        rec = find_record("H253")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["mark"], "H253")

    def test_find_by_mark_case_insensitive_with_spaces(self):
        rec = find_record("  h253 ")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["mark"], "H253")

    def test_find_by_member_name(self):
        rec = find_record("UB254x146x37")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["mark"], "H253")

    def test_find_by_member_name_case_and_space_insensitive(self):
        rec = find_record("ub 254 X 146 x 37")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["mark"], "H253")

    def test_no_partial_match(self):
        # "H25" should NOT match H253/H254/H255 - only exact matches are valid.
        self.assertIsNone(find_record("H25"))

    def test_no_closest_match_for_unknown_mark(self):
        self.assertIsNone(find_record("H999"))

    def test_empty_query_returns_none(self):
        self.assertIsNone(find_record(""))
        self.assertIsNone(find_record("   "))


class TestGetRecordByMark(unittest.TestCase):
    def test_known_mark(self):
        rec = get_record_by_mark("H602")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["member"], "UB610x305x149")

    def test_unknown_mark(self):
        self.assertIsNone(get_record_by_mark("H999"))


class TestAllTwentyRecords(unittest.TestCase):
    def test_exactly_twenty_records(self):
        self.assertEqual(len(CB1_H_SHAPE), 20)

    def test_all_expected_marks_present(self):
        marks = {rec["mark"] for rec in CB1_H_SHAPE}
        self.assertEqual(marks, set(EXPECTED_MARKS))

    def test_marks_are_unique(self):
        marks = [rec["mark"] for rec in CB1_H_SHAPE]
        self.assertEqual(len(marks), len(set(marks)))

    def test_members_are_unique(self):
        members = [rec["member"] for rec in CB1_H_SHAPE]
        self.assertEqual(len(members), len(set(members)))

    def test_get_marks_sorted_and_complete(self):
        self.assertEqual(get_marks(), sorted(EXPECTED_MARKS))

    def test_every_record_has_four_bolts(self):
        for rec in CB1_H_SHAPE:
            self.assertEqual(rec["bolt_count"], 4, msg=rec["mark"])

    def test_every_record_bolt_size_keeps_inch_notation(self):
        for rec in CB1_H_SHAPE:
            self.assertIn("in", rec["bolt_size"], msg=rec["mark"])

    def test_bolt_grid_spans_do_not_exceed_plate(self):
        for rec in CB1_H_SHAPE:
            plate_x, plate_y = rec["plate_xy_mm"]
            grid = rec["bolt_grid_mm"]
            span_x = grid["edge_x"] * 2 + grid["pitch_x"]
            span_y = grid["edge_y"] * 2 + grid["pitch_y"]
            self.assertLessEqual(span_x, plate_x + 0.51, msg=rec["mark"])
            self.assertLessEqual(span_y, plate_y + 0.51, msg=rec["mark"])

    def test_bolt_offsets_are_symmetric_and_within_plate(self):
        for rec in CB1_H_SHAPE:
            offs = bolt_offsets_mm(rec)
            plate_x, plate_y = rec["plate_xy_mm"]
            self.assertGreater(offs["dx"], 0, msg=rec["mark"])
            self.assertGreater(offs["dy"], 0, msg=rec["mark"])
            self.assertLessEqual(offs["dx"], plate_x / 2, msg=rec["mark"])
            self.assertLessEqual(offs["dy"], plate_y / 2, msg=rec["mark"])

    def test_all_key_dimensions_positive(self):
        for rec in CB1_H_SHAPE:
            for key in ("plate_thickness_mm", "weld_size_mm", "hole_diameter_mm", "pj_mm"):
                self.assertGreater(rec[key], 0, msg=f"{rec['mark']}.{key}")
            for key in ("section_mm", "plate_xy_mm", "pedestal_xy_mm"):
                for v in rec[key]:
                    self.assertGreater(v, 0, msg=f"{rec['mark']}.{key}")

    def test_pj_and_hole_diameter_are_millimetres_not_inches(self):
        # Only bolt_size retains inch notation; everything else is millimetres.
        for rec in CB1_H_SHAPE:
            self.assertIsInstance(rec["pj_mm"], (int, float), msg=rec["mark"])
            self.assertIsInstance(rec["hole_diameter_mm"], (int, float), msg=rec["mark"])


class TestValidateRecords(unittest.TestCase):
    def test_no_validation_errors(self):
        errors = validate_records()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()