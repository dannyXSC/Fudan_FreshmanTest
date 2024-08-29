from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.common.by import By

def take_exam(driver: WebDriver):
    take_quiz_link = driver.find_elements(By.ID, "take_quiz_link")
    if take_quiz_link:
        take_quiz_link[0].click()
    else:
        take_quiz_button_link = driver.find_elements(By.CSS_SELECTOR, "div.take_quiz_button a.btn.btn-primary")
        if take_quiz_button_link:
            take_quiz_button_link[0].click()


def submit_exam(driver: WebDriver):
    driver.find_element(By.ID, "submit_quiz_button").click()
    alert = driver.switch_to.alert
    alert.accept()


def goto_next_question(driver: WebDriver):
    target = driver.find_elements(By.CLASS_NAME, "next-question")
    if len(target) == 0:
        return None
    target[0].click()
    return True


def generate_answer(driver: WebDriver):
    take_exam(driver)
    submit_exam(driver)
