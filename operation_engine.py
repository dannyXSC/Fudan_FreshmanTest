from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


TAKE_SELECTORS = (
    (By.ID, "take_quiz_link"),
    (By.CSS_SELECTOR, "div.take_quiz_button a.btn.btn-primary"),
    (By.CSS_SELECTOR, "a[href*='/quizzes/'][href$='/take']"),
    (By.CSS_SELECTOR, "form[action*='/quizzes/'][action$='/take'] input[type='submit']"),
)
SUBMIT_SELECTORS = (
    (By.ID, "submit_quiz_button"),
    (By.CSS_SELECTOR, ".submit_quiz_button"),
    (By.CSS_SELECTOR, "button[type='submit'][name='submit_quiz']"),
    (By.CSS_SELECTOR, "form[action*='quiz_submissions'] button[type='submit']"),
)
QUESTION_SELECTORS = (
    (By.CSS_SELECTOR, ".question_holder"),
    (By.CSS_SELECTOR, "#questions .question"),
)


def _first_visible(driver, selectors):
    for by, value in selectors:
        for element in driver.find_elements(by, value):
            if element.is_displayed() and element.is_enabled():
                return element, (by, value)
    return None, None


def inspect_quiz_page(driver: WebDriver):
    take, take_selector = _first_visible(driver, TAKE_SELECTORS)
    submit, submit_selector = _first_visible(driver, SUBMIT_SELECTORS)
    question_count = max(
        (len(driver.find_elements(by, value)) for by, value in QUESTION_SELECTORS),
        default=0,
    )
    return {
        "url": driver.current_url,
        "title": driver.title,
        "take_or_resume_found": take is not None,
        "take_or_resume_selector": take_selector,
        "question_count": question_count,
        "submit_found": submit is not None,
        "submit_selector": submit_selector,
    }


def take_exam(driver: WebDriver, allow_state_change=False):
    if not allow_state_change:
        raise PermissionError("Refusing to start/resume quiz without allow_state_change=True")
    element, selector = _first_visible(driver, TAKE_SELECTORS)
    if element is None:
        if inspect_quiz_page(driver)["question_count"]:
            return None
        raise LookupError("No start/resume quiz control matched the supported selectors")
    element.click()
    WebDriverWait(driver, 30).until(
        lambda current: inspect_quiz_page(current)["question_count"] > 0
    )
    return selector


def submit_exam(driver: WebDriver, allow_submit=False):
    if not allow_submit:
        raise PermissionError("Refusing to submit quiz without allow_submit=True")
    element, selector = _first_visible(driver, SUBMIT_SELECTORS)
    if element is None:
        raise LookupError("No quiz submit control matched the supported selectors")
    element.click()
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except (TimeoutException, NoAlertPresentException):
        pass
    WebDriverWait(driver, 30).until(
        lambda current: "/take" not in current.current_url
        or "submission" in current.current_url
    )
    return selector


def goto_next_question(driver: WebDriver):
    signature_script = """
        const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
        let questions = [...document.querySelectorAll('.question_holder')];
        if (!questions.length) questions = [...document.querySelectorAll('#questions .question')];
        const question = questions.find(visible);
        if (!question) return '';
        const stem = question.querySelector('.question_text') || question.querySelector('.question_name');
        return `${question.id || ''}|${(stem?.innerText || '').replace(/\\s+/g, ' ').trim()}`;
    """
    before = driver.execute_script(signature_script)
    navigation = driver.execute_script(
        """
        const items = [...document.querySelectorAll('.list_question')];
        return {
          total: items.length,
          current: items.findIndex(item => item.classList.contains('current_question')),
        };
        """
    )
    if navigation["total"] and navigation["current"] >= navigation["total"] - 1:
        return None
    clicked = driver.execute_script(
        """
        const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
        const button = [...document.querySelectorAll('.next-question')]
          .find(el => visible(el) && !el.disabled && el.getAttribute('aria-disabled') !== 'true');
        if (!button) return false;
        button.click();
        return true;
        """
    )
    if not clicked:
        return None
    WebDriverWait(driver, 15).until(
        lambda current: (
            (signature := current.execute_script(signature_script))
            and signature != before
        )
    )
    return True


def goto_first_question(driver: WebDriver):
    navigation = driver.execute_script(
        """
        const items = [...document.querySelectorAll('.list_question')];
        return {
          total: items.length,
          current: items.findIndex(item => item.classList.contains('current_question')),
        };
        """
    )
    if not navigation["total"] or navigation["current"] <= 0:
        return False
    clicked = driver.execute_script(
        """
        const first = document.querySelector('.list_question');
        const target = first?.querySelector('a') || first;
        if (!target) return false;
        target.click();
        return true;
        """
    )
    if not clicked:
        return False
    WebDriverWait(driver, 15).until(
        lambda current: current.execute_script(
            """
            const items = [...document.querySelectorAll('.list_question')];
            return items.findIndex(item => item.classList.contains('current_question')) === 0;
            """
        )
    )
    return True


def generate_answer(driver: WebDriver, allow_state_change=False, allow_submit=False):
    take_exam(driver, allow_state_change=allow_state_change)
    return submit_exam(driver, allow_submit=allow_submit)
