import unittest

from python.photo_match import _label_from_text, matches_report


class PhotoMatchTests(unittest.TestCase):
    def test_one_word(self) -> None:
        self.assertEqual(_label_from_text("collision"), "collision")
        self.assertEqual(_label_from_text("GLASS."), "glass")

    def test_sentence(self) -> None:
        self.assertEqual(
            _label_from_text("The image shows a collision of two cars."),
            "collision",
        )
        self.assertEqual(_label_from_text("flooded garage"), "flood")

    def test_other(self) -> None:
        self.assertEqual(_label_from_text("a cat on a sofa"), "other")
        self.assertEqual(_label_from_text(""), "other")

    def test_match_peril(self) -> None:
        self.assertTrue(matches_report("collision", "collision"))
        self.assertFalse(matches_report("flood", "collision"))
        self.assertFalse(matches_report("other", "collision"))
