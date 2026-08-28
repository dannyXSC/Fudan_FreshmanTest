import io
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from environment import (
    browser_profile_path,
    cookie_path,
    input_wait_time,
    main_page,
    page_load_timeout,
)

DRIVER_PATH = Path(__file__).resolve().parent / ".runtime" / "chromedriver.exe"
KNOWN_GOOD_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
)
MIRROR_TEMPLATE = (
    "https://registry.npmmirror.com/-/binary/chrome-for-testing/{version}/win64/chromedriver-win64.zip"
)


def _chrome_exe():
    candidates = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    return next((str(path) for path in candidates if path.is_file()), None)


def _chrome_major():
    """Major version of the installed Chrome, or None if it cannot be read."""
    chrome = _chrome_exe()
    if not chrome:
        return None
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Item '{chrome}').VersionInfo.ProductVersion",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip().split(".")[0] or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _driver_matches(driver_path, major):
    """True if the driver's version starts with Chrome's major version."""
    try:
        result = subprocess.run(
            [str(driver_path), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip().split()[1].startswith(f"{major}.")
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return False


def _download_matching_driver(major):
    """Download a chromedriver matching Chrome's major version from the mirror.

    Returns the driver path on success, or None so the caller can fall back to
    Selenium Manager (Google's download source) as a last resort.
    """
    try:
        with urllib.request.urlopen(KNOWN_GOOD_URL, timeout=60) as response:
            known_good = json.load(response)
        candidates = [
            version["version"]
            for version in known_good["versions"]
            if version["version"].startswith(f"{major}.")
        ]
        if not candidates:
            print(
                f"WARNING: no chromedriver listed for Chrome {major}",
                file=sys.stderr,
                flush=True,
            )
            return None
        version = candidates[-1]
        url = MIRROR_TEMPLATE.format(version=version)
        print(f"Downloading chromedriver {version} from mirror...", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        DRIVER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            member = next(
                name for name in archive.namelist() if name.endswith("chromedriver.exe")
            )
            with archive.open(member) as src, open(DRIVER_PATH, "wb") as dst:
                shutil.copyfileobj(src, dst)
        print(f"Installed driver at {DRIVER_PATH}", flush=True)
        return str(DRIVER_PATH)
    except Exception as exc:  # any failure falls back to Selenium Manager
        print(
            f"WARNING: mirror download failed ({exc}); "
            "falling back to Selenium Manager.",
            file=sys.stderr,
            flush=True,
        )
        return None


def _resolve_driver_path():
    """Resolve a chromedriver path: local driver first, then the mirror.

    Selenium Manager's automatic download hits googlechromelabs.github.io and
    storage.googleapis.com, which are often unreachable on CN networks and make
    ``webdriver.Chrome()`` hang. Prefer a local driver and the npmmirror mirror
    so driver creation never blocks on Google's endpoints.
    """
    major = _chrome_major()
    if not major:
        # Chrome version unreadable; use whatever local driver exists.
        return str(DRIVER_PATH) if DRIVER_PATH.is_file() else None
    if DRIVER_PATH.is_file():
        if _driver_matches(DRIVER_PATH, major):
            return str(DRIVER_PATH)
        print(
            f"Local driver is stale for Chrome {major}; refreshing...", flush=True
        )
    return _download_matching_driver(major)


def create_driver(headless=False, profile_path=browser_profile_path):
    """Create Chrome with a locally-resolved chromedriver.

    Resolution priority: local driver -> npmmirror mirror -> Selenium Manager.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    if profile_path:
        profile = Path(profile_path).resolve()
        profile.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile}")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    service = None
    driver_path = _resolve_driver_path()
    if driver_path:
        service = webdriver.ChromeService(executable_path=driver_path)
    browser = webdriver.Chrome(options=options, service=service)
    browser.set_page_load_timeout(page_load_timeout)
    return browser


def _is_target_quiz(current_url, target_url):
    current = urlparse(current_url)
    target = urlparse(target_url)
    return current.netloc == target.netloc and target.path in current.path


def wait_for_manual_auth(browser, target_url=main_page, timeout=input_wait_time):
    try:
        WebDriverWait(browser, timeout).until(
            lambda driver: _is_target_quiz(driver.current_url, target_url)
        )
    except TimeoutException as exc:
        raise TimeoutException(
            f"Login did not reach the target quiz within {timeout} seconds; "
            f"current URL: {browser.current_url}"
        ) from exc
    return browser


def driver_manual_auth(
    url=main_page,
    headless=False,
    timeout=input_wait_time,
    profile_path=browser_profile_path,
):
    browser = create_driver(headless=headless, profile_path=profile_path)
    browser.get(url)
    return wait_for_manual_auth(browser, url, timeout)


def load_cookies(log_url, browser, path=cookie_path):
    """Explicitly save cookies; this is not called by the default workflow."""
    browser.get(log_url)
    input("Complete login in Chrome, then press Enter here to save cookies...")
    Path(path).write_text(
        json.dumps(browser.get_cookies(), ensure_ascii=False), encoding="utf-8"
    )


def get_cookies(browser, path=cookie_path):
    cookies = json.loads(Path(path).read_text(encoding="utf-8"))
    for cookie in cookies:
        if cookie.get("sameSite") not in {None, "Strict", "Lax", "None"}:
            cookie.pop("sameSite", None)
        browser.add_cookie(cookie)


def driver_get_with_cookies(url=main_page, path=cookie_path, headless=False):
    if not os.path.exists(path):
        return driver_manual_auth(url, headless=headless)
    browser = create_driver(headless=headless, profile_path=browser_profile_path)
    origin = urlparse(url)
    browser.get(f"{origin.scheme}://{origin.netloc}/")
    get_cookies(browser, path)
    browser.get(url)
    return wait_for_manual_auth(browser, url, timeout=30)
