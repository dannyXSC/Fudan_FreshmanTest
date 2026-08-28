import unittest

from environment import question_path
from question_engine import load_question_list


class QuestionBankTests(unittest.TestCase):
    def test_bank_entries_are_complete_and_unique(self):
        questions = load_question_list(question_path)
        variants = {(question.stem, tuple(question.answers)) for question in questions}
        self.assertGreaterEqual(len(questions), 150)
        self.assertEqual(len(variants), len(questions))
        self.assertTrue(all(question.is_usable for question in questions))


if __name__ == "__main__":
    unittest.main()
