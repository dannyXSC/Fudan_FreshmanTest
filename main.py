import argparse
import json

from cookie_engine import driver_get_with_cookies, driver_manual_auth
from environment import cookie_path, input_wait_time, main_page, question_path
from operation_engine import inspect_quiz_page, take_exam
from question_engine import answer_all_questions, load_question_list, question_list_to_dict


def parse_args():
    parser = argparse.ArgumentParser(description="Fudan 2026 freshman quiz helper")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="start/resume the quiz and select answers; default is read-only inspection",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="submit after answering; requires --execute",
    )
    parser.add_argument("--use-cookies", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--auto-close",
        action="store_true",
        help="close Chrome immediately after completion; intended for automated tests",
    )
    parser.add_argument("--login-timeout", type=int, default=input_wait_time)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.submit and not args.execute:
        raise SystemExit("--submit requires --execute")

    if args.use_cookies:
        driver = driver_get_with_cookies(main_page, cookie_path, headless=args.headless)
    else:
        driver = driver_manual_auth(
            main_page, headless=args.headless, timeout=args.login_timeout
        )
    try:
        inspection = inspect_quiz_page(driver)
        print(json.dumps(inspection, ensure_ascii=False, indent=2))
        if not args.execute:
            print("DRY RUN: no controls were clicked and quiz state was not changed.")
            return 0

        questions = load_question_list(question_path)
        usable = sum(question.is_usable for question in questions)
        print(f"Question bank: {usable}/{len(questions)} usable entries", flush=True)
        take_exam(driver, allow_state_change=True)
        result = answer_all_questions(
            driver,
            question_list_to_dict(questions),
            allow_submit=args.submit,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.submit:
            print("Answers were selected but the quiz was not submitted.")
        return 0
    finally:
        if not args.auto_close and not args.headless:
            try:
                input("Press Enter to close Chrome...")
            except EOFError:
                pass
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
