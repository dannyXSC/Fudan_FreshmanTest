"""Runtime configuration for the 2026 freshman quiz."""

from pathlib import Path


project_root = Path(__file__).resolve().parent

auth_url = "https://id.fudan.edu.cn/"
main_page = (
    "https://elearning.fudan.edu.cn/courses/113489/quizzes/14232"
    "?module_item_id=229765"
)

cookie_path = str(project_root / "asset" / "cookies.txt")
question_path = str(project_root / "asset" / "questions.json")
browser_profile_path = str(project_root / ".runtime" / "chrome-profile")

# Kept for compatibility with the original module imports.
if_load_cookie = False
if_add_question = True

input_wait_time = 300
page_load_timeout = 45
