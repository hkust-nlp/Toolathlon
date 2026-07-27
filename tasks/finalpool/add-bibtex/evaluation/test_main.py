import io
import unittest
from contextlib import redirect_stdout

from main import entries_match, normalize_field_value


class NormalizeFieldValueTests(unittest.TestCase):
    def test_latex_and_unicode_accents_match_ascii_author_name(self):
        variants = (
            r"Rozi{\`e}re",
            r"Rozi\`{e}re",
            r"Rozi{\`{e}}re",
            "Rozière",
            "Roziere",
            r"Rozi{e}re",
        )

        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(
                    normalize_field_value(variant, "author"),
                    "roziere",
                )

    def test_other_common_latex_accents_are_folded(self):
        equivalent_pairs = (
            (r"Marasovi{\'c}", "Marasovic"),
            (r'M{\"u}ller', "Muller"),
            (r"Mu{\~n}oz", "Munoz"),
            (r"Fran{\c{c}}ois", "Francois"),
            (r"S{\o}ren", "Soren"),
        )

        for latex_name, ascii_name in equivalent_pairs:
            with self.subTest(latex_name=latex_name):
                self.assertEqual(
                    normalize_field_value(latex_name, "author"),
                    normalize_field_value(ascii_name, "author"),
                )

    def test_title_formatting_and_escapes_are_normalized(self):
        self.assertEqual(
            normalize_field_value(r"\textbf{Code Llama}", "title"),
            normalize_field_value("Code Llama", "title"),
        )
        self.assertEqual(
            normalize_field_value(r"Q\&A", "title"),
            normalize_field_value("Q&A", "title"),
        )
        self.assertEqual(
            normalize_field_value(r"{{Code} {Llama}}", "title"),
            normalize_field_value("Code Llama", "title"),
        )

    def test_and_others_remains_semantically_required(self):
        truncated = "Roziere, Baptiste and Gehring, Jonas and others"
        marker_omitted = "Roziere, Baptiste and Gehring, Jonas"
        full = "Roziere, Baptiste and Gehring, Jonas and Gloeckle, Fabian"

        normalized = normalize_field_value(truncated, "author")
        self.assertIn("and others", normalized)
        self.assertNotEqual(
            normalized,
            normalize_field_value(marker_omitted, "author"),
        )
        self.assertNotEqual(
            normalized,
            normalize_field_value(full, "author"),
        )
        self.assertNotEqual(
            normalized,
            normalize_field_value(
                "Roziere, Baptiste and Gehring, Jonas and et al.",
                "author",
            ),
        )


class EntriesMatchTests(unittest.TestCase):
    @staticmethod
    def _entry(author, entry_id="roziere2023code", **extra_fields):
        entry = {
            "ID": entry_id,
            "ENTRYTYPE": "article",
            "title": "Code llama: Open foundation models for code",
            "author": author,
            "year": "2023",
        }
        entry.update(extra_fields)
        return entry

    def test_different_key_and_extra_fields_are_allowed(self):
        expected = self._entry(
            "Roziere, Baptiste and Gehring, Jonas and others",
        )
        actual = self._entry(
            r"Rozi{\`e}re, Baptiste and Gehring, Jonas and others",
            entry_id="roziere2023codellama",
            doi="10.0000/example",
        )

        self.assertTrue(entries_match(expected, actual))

    def test_missing_required_field_is_rejected(self):
        expected = self._entry("A and B and others")
        actual = self._entry("A and B and others")
        del actual["year"]

        with redirect_stdout(io.StringIO()):
            self.assertFalse(entries_match(expected, actual))

    def test_full_author_list_does_not_replace_and_others(self):
        expected = self._entry("A and B and others")
        actual = self._entry("A and B and C")

        with redirect_stdout(io.StringIO()):
            self.assertFalse(entries_match(expected, actual))


if __name__ == "__main__":
    unittest.main()
