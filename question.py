import re


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


class Question(object):
    def __init__(self, stem="", answers=None, correct_answers=None):
        self.stem = normalize_text(stem)
        self.answers = [normalize_text(item) for item in (answers or [])]
        self.correct_answers = [
            normalize_text(item) for item in (correct_answers or [])
        ]
        self.answers_set = set(self.answers)
        self.correct_answers_set = set(self.correct_answers)

    def to_dict(self):
        return {
            "stem": self.stem,
            "answers": self.answers,
            "correct_answers": self.correct_answers,
        }

    def equal(self, other):
        return self.stem == other.stem and self.answers_set == other.answers_set

    @property
    def is_usable(self):
        return bool(self.correct_answers_set) and self.correct_answers_set.issubset(
            self.answers_set
        )

    @classmethod
    def from_dict(cls, data):
        return cls(data["stem"], data["answers"], data["correct_answers"])
