import argparse
import json
import shutil
from pathlib import Path

from selenium.webdriver.support.ui import WebDriverWait

from cookie_engine import driver_get_with_cookies, driver_manual_auth
from environment import cookie_path, input_wait_time, main_page, question_path
from operation_engine import generate_answer, inspect_quiz_page
from question_engine import (
    get_questions_answers,
    load_question_list,
    question_list_merge,
    save_question_list,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update the question bank from a submitted attempt result"
    )
    parser.add_argument(
        "--update-bank",
        action="store_true",
        help="submit the current attempt and merge revealed correct answers",
    )
    parser.add_argument(
        "--confirm-attempt-submit",
        "--confirm-empty-submit",
        dest="confirm_attempt_submit",
        action="store_true",
        help="required acknowledgement that the current attempt will be submitted",
    )
    parser.add_argument("--use-cookies", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--auto-close",
        action="store_true",
        help="close Chrome immediately after completion; intended for automated tests",
    )
    parser.add_argument("--login-timeout", type=int, default=input_wait_time)
    parser.add_argument("--output", default=question_path)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.update_bank and not args.confirm_attempt_submit:
        raise SystemExit(
            "Refusing to submit the current attempt: add --confirm-attempt-submit"
        )

    if args.use_cookies:
        driver = driver_get_with_cookies(main_page, cookie_path, headless=args.headless)
    else:
        driver = driver_manual_auth(
            main_page, headless=args.headless, timeout=args.login_timeout
        )
    try:
        print(json.dumps(inspect_quiz_page(driver), ensure_ascii=False, indent=2))
        if not args.update_bank:
            print("DRY RUN: the quiz was not started and no attempt was submitted.")
            return 0

        generate_answer(
            driver,
            allow_state_change=True,
            allow_submit=True,
        )
        scraped = WebDriverWait(driver, 30).until(
            lambda current: get_questions_answers(current) or False
        )
        output = Path(args.output)
        existing = load_question_list(output) if output.exists() else []
        if output.exists():
            backup = output.with_name(f"{output.stem}.before_2026{output.suffix}")
            if not backup.exists():
                shutil.copy2(output, backup)
                print(f"Backup: {backup}")
        stats = question_list_merge(existing, scraped)
        save_question_list(existing, output)
        print(json.dumps({"scraped": len(scraped), **stats}, ensure_ascii=False, indent=2))
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
