"""
Pytest configuration for browser-based testing with Playwright and HTML report customization.
"""

import io
import atexit
import logging
from pathlib import Path
from venv import logger

import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config.constants import URL

# Global dictionary to store log streams for each test
LOG_STREAMS = {}


@pytest.fixture(scope="session")
def login_logout():
    """
    Fixture to launch the browser, log in, and yield the page object.
    Closes the browser after the session ends.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        context.set_default_timeout(80000)
        page = context.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        # Uncomment and complete the following to enable login
        # login_page = LoginPage(page)
        # load_dotenv()
        # login_page.authenticate(os.getenv("user_name"), os.getenv("pass_word"))

        yield page

        browser.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """
    Pytest hook to set up a log capture for each test.
    """
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.addHandler(handler)

    LOG_STREAMS[item.nodeid] = (handler, stream)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Pytest hook to add captured logs to the test report.
    """
    outcome = yield
    report = outcome.get_result()

    handler, stream = LOG_STREAMS.get(item.nodeid, (None, None))

    if handler and stream:
        handler.flush()
        log_output = stream.getvalue()

        logger = logging.getLogger()
        logger.removeHandler(handler)

        report.description = f"<pre>{log_output.strip()}</pre>"

        LOG_STREAMS.pop(item.nodeid, None)
    else:
        report.description = ""


def pytest_collection_modifyitems(items):
    """
    Modify test node IDs based on the test's parameterized 'prompt' value.
    """
    for item in items:
        if hasattr(item, "callspec"):
            prompt = item.callspec.params.get("prompt")
            if prompt:
                item._nodeid = prompt


def rename_duration_column():
    """
    Modify the HTML report to rename 'Duration' column to 'Execution Time'.
    Runs automatically after the test session.
    """
    report_path = Path("report.html")
    if not report_path.exists():
        logger.info("Report file not found, skipping column rename.")
        return

    with report_path.open("r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    headers = soup.select("table#results-table thead th")
    for th in headers:
        if th.text.strip() == "Duration":
            th.string = "Execution Time"
            break
    else:
        print("'Duration' column not found in report.")

    with report_path.open("w", encoding="utf-8") as file:
        file.write(str(soup))


# Register HTML report column modification
atexit.register(rename_duration_column)
