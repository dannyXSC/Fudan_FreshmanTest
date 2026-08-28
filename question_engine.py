import json
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from operation_engine import goto_first_question, goto_next_question, submit_exam
from question import Question, normalize_text


QUESTION_SELECTOR = ".question_holder, #questions .question"


def _question_elements(browser):
    return browser.find_elements(By.CSS_SELECTOR, QUESTION_SELECTOR)


def _first_text(root, selectors):
    for selector in selectors:
        for element in root.find_elements(By.CSS_SELECTOR, selector):
            text = normalize_text(element.text)
            if text:
                return text
    return ""


def _answer_rows(question):
    rows = question.find_elements(By.CSS_SELECTOR, ".answer")
    if rows:
        return rows
    return question.find_elements(By.CSS_SELECTOR, "label.answer_label, .answer_label")


def _answer_text(row):
    text = _first_text(row, (".answer_text", "label"))
    return text or normalize_text(row.text)


def _unique(items):
    result = []
    seen = set()
    for item in items:
        value = normalize_text(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _correct_answer_texts(question):
    correct = []
    for row in question.find_elements(
        By.CSS_SELECTOR,
        ".answer.correct_answer, .answer.correct, [data-correct-answer='true']",
    ):
        correct.append(_answer_text(row))

    # Compatibility with the result-page markup used by the original project.
    for info in question.find_elements(By.CSS_SELECTOR, ".info[id]"):
        raw_id = info.get_attribute("id") or ""
        answer_id = raw_id.split("_", 1)[-1]
        for selector in (
            f"label[for='answer-{answer_id}']",
            f"label[for$='_{answer_id}']",
        ):
            labels = question.find_elements(By.CSS_SELECTOR, selector)
            if labels:
                correct.append(_answer_text(labels[0]))
                break
    return _unique(correct)


def get_questions_answers(browser: WebDriver):
    question_list = []
    for element in _question_elements(browser):
        stem = _first_text(element, (".question_text", ".question_name"))
        answers = _unique(_answer_text(row) for row in _answer_rows(element))
        correct_answers = _correct_answer_texts(element)
        if stem and answers and correct_answers:
            question_list.append(Question(stem, answers, correct_answers))
    return question_list


def question_list_to_dict(question_list):
    result = {}
    for question in question_list:
        if not question.is_usable:
            continue
        result.setdefault(question.stem, []).append(question)
    return result


def question_list_merge(existing, incoming):
    """Merge incoming questions into existing and replace matching old answers."""
    by_stem = question_list_to_dict(existing)
    added = 0
    replaced = 0
    for question in incoming:
        matches = by_stem.get(question.stem, [])
        match = next((item for item in matches if item.equal(question)), None)
        if match is None:
            existing.append(question)
            by_stem.setdefault(question.stem, []).append(question)
            added += 1
        elif match.correct_answers_set != question.correct_answers_set:
            match.correct_answers = list(question.correct_answers)
            match.correct_answers_set = set(question.correct_answers)
            replaced += 1
    return {"added": added, "replaced": replaced, "total": len(existing)}


def _matching_bank_question(current, question_dict):
    return next(
        (
            saved
            for saved in question_dict.get(current.stem, [])
            if saved.is_usable and current.equal(saved)
        ),
        None,
    )


PAGE_QUESTIONS_SCRIPT = r"""
    const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
    const visible = element => !!(
      element.offsetWidth || element.offsetHeight || element.getClientRects().length
    );
    let questions = [...document.querySelectorAll('.question_holder')];
    if (!questions.length) questions = [...document.querySelectorAll('#questions .question')];
    return questions
      .filter(visible)
      .map((question, index) => {
        let rows = [...question.querySelectorAll('.answer')];
        if (!rows.length) rows = [...question.querySelectorAll('label.answer_label, .answer_label')];
        const answers = rows.map(row => {
          const text = row.querySelector('.answer_text') || row.querySelector('label') || row;
          return normalize(text.innerText || text.textContent);
        }).filter(Boolean);
        const stemNode = question.querySelector('.question_text') || question.querySelector('.question_name');
        return {
          index,
          key: question.id || normalize(stemNode?.innerText),
          stem: normalize(stemNode?.innerText),
          answers,
        };
      });
"""


APPLY_ANSWERS_SCRIPT = r"""
    const questionIndex = arguments[0];
    const expected = arguments[1];
    const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
    const visible = element => !!(
      element.offsetWidth || element.offsetHeight || element.getClientRects().length
    );
    const desired = new Set(expected.map(normalize));
    let questions = [...document.querySelectorAll('.question_holder')];
    if (!questions.length) questions = [...document.querySelectorAll('#questions .question')];
    questions = questions.filter(visible);
    const question = questions[questionIndex];
    if (!question) return {changed: 0, selected: []};
    let rows = [...question.querySelectorAll('.answer')];
    if (!rows.length) rows = [...question.querySelectorAll('label.answer_label, .answer_label')];
    const parsed = rows.map(row => {
      const textNode = row.querySelector('.answer_text') || row.querySelector('label') || row;
      const input = row.querySelector("input[type='radio'], input[type='checkbox']") ||
        (row.matches("input[type='radio'], input[type='checkbox']") ? row : null);
      const label = row.querySelector('label') ||
        (row.matches('label') ? row : null) ||
        (input?.id ? question.querySelector(`label[for="${CSS.escape(input.id)}"]`) : null);
      return {row, text: normalize(textNode.innerText || textNode.textContent), input, label};
    });
    let changed = 0;
    for (const item of parsed.filter(item => desired.has(item.text))) {
      if (item.input && !item.input.checked) {
        (item.label || item.input).click();
        changed += 1;
      }
    }
    for (const item of parsed.filter(item => !desired.has(item.text))) {
      if (item.input?.type === 'checkbox' && item.input.checked) {
        (item.label || item.input).click();
        changed += 1;
      }
    }
    return {
      changed,
      selected: parsed.filter(item => item.input?.checked).map(item => item.text),
    };
"""


def _page_questions(browser):
    return browser.execute_script(PAGE_QUESTIONS_SCRIPT)


def _answer_page(browser, question_dict):
    answered = 0
    missing = []
    details = []
    for record in _page_questions(browser):
        current = Question(stem=record["stem"], answers=record["answers"])
        saved = _matching_bank_question(current, question_dict)
        if saved is None:
            missing.append(current.stem)
            details.append({"stem": current.stem, "matched": False})
            continue
        applied = browser.execute_script(
            APPLY_ANSWERS_SCRIPT,
            record["index"],
            list(saved.correct_answers),
        )
        selected = set(applied["selected"])
        if selected != saved.correct_answers_set:
            missing.append(current.stem)
            details.append({"stem": current.stem, "matched": False})
            continue
        answered += 1
        details.append(
            {
                "stem": current.stem,
                "matched": True,
                "selected": applied["selected"],
            }
        )
    return answered, missing, details


def answer_questions_on_page(browser: WebDriver, question_dict):
    answered, missing, _ = _answer_page(browser, question_dict)
    return answered, missing


def answer_question(browser: WebDriver, question_dict):
    answered, _ = answer_questions_on_page(browser, question_dict)
    return answered


def answer_all_questions(
    browser: WebDriver,
    question_dict,
    allow_submit=False,
    max_questions=200,
):
    answered = 0
    missing = []
    visited = set()
    processed = 0
    total = browser.execute_script(
        "return document.querySelectorAll('.list_question').length"
    )
    goto_first_question(browser)
    for _ in range(max_questions):
        records = WebDriverWait(browser, 15).until(
            lambda current: _page_questions(current) or False
        )
        page_key = tuple(
            (record["stem"], tuple(record["answers"])) for record in records
        )
        if not page_key or page_key in visited:
            break
        visited.add(page_key)
        count, page_missing, details = _answer_page(browser, question_dict)
        answered += count
        missing.extend(page_missing)
        for detail in details:
            processed += 1
            status = "命中" if detail["matched"] else "题库缺失"
            total_text = str(total) if total else "?"
            print(f"第 {processed}/{total_text} 题：{status}", flush=True)
        if goto_next_question(browser) is None:
            break
    complete = not total or processed >= total
    if allow_submit:
        if missing or not complete:
            raise RuntimeError(
                "Refusing to submit: not every question was processed and matched"
            )
        submit_exam(browser, allow_submit=True)
    return {
        "processed": processed,
        "total": total,
        "answered": answered,
        "missing": _unique(missing),
        "complete": complete,
    }


def save_question_list(question_list, path):
    Path(path).write_text(
        json.dumps(
            [question.to_dict() for question in question_list],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_question_list(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Question.from_dict(question) for question in data]
