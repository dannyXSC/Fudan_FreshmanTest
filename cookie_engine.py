import json
import time
from selenium import webdriver

from environment import driver_path, auth_url, cookie_path


def load_cookies(log_url, browser):
    """
    获取cookies保存至本地
    """
    browser.get(log_url)
    time.sleep(15)  # 进行扫码
    dictCookies = browser.get_cookies()  # 获取list的cookies
    jsonCookies = json.dumps(dictCookies)  # 转换成字符串保存

    with open(cookie_path, 'w') as f:
        f.write(jsonCookies)
    print('cookies保存成功！')


def get_cookies(browser):
    with open(cookie_path, 'r', encoding='utf8') as f:
        listCookies = json.loads(f.read())
    for cookie in listCookies:
        browser.add_cookie(cookie)


if __name__ == '__main__':
    driver = webdriver.Chrome(executable_path=driver_path)
    load_cookies(auth_url, driver)
