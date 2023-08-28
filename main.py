import json
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from cookie_engine import get_cookies, load_cookies
from environment import driver_path, main_page, cookie_path, auth_url, if_load_cookie, question_path, if_load_question, \
    if_add_question
from operation_engine import take_exam, submit_exam, generate_answer
from question import Question
from question_engine import get_questions_answers, question_list_to_dict, question_list_merge, answer_question, \
    answer_all_questions

driver = webdriver.Chrome(executable_path=driver_path)

if not os.path.exists(cookie_path) or if_load_cookie:
    load_cookies(auth_url, driver)

# 载入cookie
driver.get(main_page)
get_cookies(driver)
driver.refresh()

if not os.path.exists(question_path) or if_load_question:
    print("-------------------开始获得答案信息------------------")
    question_list_old = []
    if if_add_question:
        with open(question_path, 'r', encoding='utf8') as f:
            question_list_old = json.loads(f.read())
        question_list_old = [Question.from_dict(question) for question in question_list_old]

    generate_answer(driver)
    question_list = get_questions_answers(driver)
    question_list_merge(question_list, question_list_old)
    question_to_save = [question.to_dict() for question in question_list]
    with open(question_path, 'w') as f:
        f.write(json.dumps(question_to_save))

with open(question_path, 'r', encoding='utf8') as f:
    question_list = json.loads(f.read())
question_list = [Question.from_dict(question) for question in question_list]
question_dict = question_list_to_dict(question_list)

print("-------------------开始答题------------------")
take_exam(driver)
answer_all_questions(driver, question_dict)

time.sleep(10)
driver.quit()
