import tempfile
import unittest
from pathlib import Path

from operation_engine import submit_exam, take_exam
from question import Question, normalize_text
from question_engine import (
    load_question_list,
    question_list_merge,
    save_question_list,
)


class CoreTests(unittest.TestCase):
    def test_normalize_and_compare_question(self):
        left = Question("  题目\n文本 ", [" A ", "B"], ["A"])
        right = Question("题目 文本", ["B", "A"], ["A"])
        self.assertEqual(normalize_text(" a\n b "), "a b")
        self.assertTrue(left.equal(right))

    def test_merge_adds_and_replaces(self):
        existing = [Question("题目一", ["A", "B"], ["A"])]
        incoming = [
            Question("题目一", ["A", "B"], ["B"]),
            Question("题目二", ["C", "D"], ["C"]),
        ]
        stats = question_list_merge(existing, incoming)
        self.assertEqual(stats, {"added": 1, "replaced": 1, "total": 2})
        self.assertEqual(existing[0].correct_answers, ["B"])

    def test_round_trip_json(self):
        questions = [Question("题目", ["甲", "乙"], ["乙"])]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            save_question_list(questions, path)
            loaded = load_question_list(path)
        self.assertEqual([q.to_dict() for q in loaded], [q.to_dict() for q in questions])

    def test_external_state_guards(self):
        with self.assertRaises(PermissionError):
            take_exam(None)
        with self.assertRaises(PermissionError):
            submit_exam(None)

    def test_polluted_bank_entry_is_not_usable(self):
        question = Question("题目", ["A", "B"], ["来自其他题目的答案"])
        self.assertFalse(question.is_usable)


if __name__ == "__main__":
    unittest.main()
