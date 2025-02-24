import os
import sys
import time
import random
import string
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from camoufox.sync_api import Camoufox
from patchright.sync_api import sync_playwright
from logmagix import Logger, Loader
from functools import wraps

DEBUG = False

def set_debug(value: bool):
    global DEBUG
    DEBUG = value

def debug(func_or_message, *args, **kwargs):
    if callable(func_or_message):
        @wraps(func_or_message)
        def wrapper(*args, **kwargs):
            if DEBUG:
                logger.debug(f"Calling {func_or_message.__name__} with args: {args}, kwargs: {kwargs}")
            result = func_or_message(*args, **kwargs)
            if DEBUG:
                logger.debug(f"{func_or_message.__name__} returned {result}")
            return result
        return wrapper
    else:
        if DEBUG:
            logger.debug(func_or_message.format(*args, **kwargs))

@dataclass
class TurnstileResult:
    turnstile_value: Optional[str]
    elapsed_time_seconds: float
    status: str
    reason: Optional[str] = None


COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}


class CustomLogger(logging.Logger):
    @staticmethod
    def format_message(level, color, message):
        timestamp = time.strftime('%H:%M:%S')
        return f"[{timestamp}] [{COLORS.get(color)}{level}{COLORS.get('RESET')}] -> {message}"

    def debug(self, message, *args, **kwargs):
        super().debug(self.format_message('DEBUG', 'MAGENTA', message), *args, **kwargs)

    def info(self, message, *args, **kwargs):
        super().info(self.format_message('INFO', 'BLUE', message), *args, **kwargs)

    def success(self, message, *args, **kwargs):
        super().info(self.format_message('SUCCESS', 'GREEN', message), *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        super().warning(self.format_message('WARNING', 'YELLOW', message), *args, **kwargs)

    def error(self, message, *args, **kwargs):
        super().error(self.format_message('ERROR', 'RED', message), *args, **kwargs)


logging.setLoggerClass(CustomLogger)
logger = logging.getLogger("TurnstileAPIServer")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


class TurnstileSolver:
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Turnstile Solver</title>
        <script
          src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadTurnstileCallback"
          async=""
          defer=""
        ></script>
      </head>
      <body>
        <!-- cf turnstile -->
      </body>
    </html>
    """

    def __init__(self, debug: bool = False, headless: Optional[bool] = False, useragent: Optional[str] = None, browser_type: str = "chromium"):
        self.debug = debug
        self.browser_type = browser_type
        self.headless = headless
        self.useragent = useragent
        self.log = Logger(github_repository="https://github.com/sexfrance/Turnstile-Solver")
        self.loader = Loader(desc="Solving captcha...", timeout=0.05)
        
        self.browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--window-position=2000,2000",
        ]

        if useragent:
            self.browser_args.append(f"--user-agent={useragent}")

        if self.headless and not self.useragent:
            self.log.warning("To solve captchas with headless mode you need to set the useragent!")

    def _setup_page(self, browser, url: str, sitekey: str, action: str = None, cdata: str = None):
        """Set up the page with Turnstile widget."""
        if self.browser_type == "chrome":
            page = browser.pages[0]
        else:
            page = browser.new_page()

        url_with_slash = url + "/" if not url.endswith("/") else url

        if self.debug:
            logger.debug(f"Navigating to URL: {url_with_slash}")

        turnstile_div = f'<div class="cf-turnstile" data-sitekey="{sitekey}"' + (f' data-action="{action}"' if action else '') + (f' data-cdata="{cdata}"' if cdata else '') + '></div>'
        page_data = self.HTML_TEMPLATE.replace("<!-- cf turnstile -->", turnstile_div)

        page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
        page.goto(url_with_slash)

        return page

    def _get_turnstile_response(self, page, max_attempts: int = 10) -> Optional[str]:
        """Attempt to retrieve Turnstile response."""
        attempts = 0

        while attempts < max_attempts:
            turnstile_check = page.eval_on_selector(
                "[name=cf-turnstile-response]",
                "el => el.value"
            )

            if turnstile_check == "":
                if self.debug:
                    logger.debug(f"Attempt {attempts + 1}: No Turnstile response yet.")

                page.evaluate("document.querySelector('.cf-turnstile').style.width = '70px'")
                page.click(".cf-turnstile")
                time.sleep(0.5)
                attempts += 1
            else:
                turnstile_element = page.query_selector("[name=cf-turnstile-response]")
                if turnstile_element:
                    return turnstile_element.get_attribute("value")
                break

        return None

    def solve(self, url: str, sitekey: str, invisible: bool = False, action: str = None, cdata: str = None) -> TurnstileResult:
        """
        Solve the Turnstile challenge and return the result.
        """
        start_time = time.time()
        if self.browser_type == "chromium":
            browser = sync_playwright().start().chromium.launch(
                headless=self.headless,
                args=self.browser_args
            )

        elif self.browser_type == "chrome":
            browser = sync_playwright().start().chromium.launch_persistent_context(
                user_data_dir=f"{os.getcwd()}/tmp/turnstile-chrome-{''.join(random.choices(string.ascii_letters + string.digits, k=10))}",
                channel="chrome",
                headless=self.headless,
                no_viewport=True,
            )

        elif self.browser_type == "camoufox":
            browser = Camoufox(headless=self.headless).start()

        try:
            page = self._setup_page(browser, url, sitekey, action, cdata)
            turnstile_value = self._get_turnstile_response(page)

            elapsed_time = round(time.time() - start_time, 3)

            if not turnstile_value:
                result = TurnstileResult(
                    turnstile_value=None,
                    elapsed_time_seconds=elapsed_time,
                    status="failure",
                    reason="Max attempts reached without token retrieval"
                )
                logger.error("Failed to retrieve Turnstile value.")
            else:
                result = TurnstileResult(
                    turnstile_value=turnstile_value,
                    elapsed_time_seconds=elapsed_time,
                    status="success"
                )
                logger.success(f"Successfully solved captcha: {turnstile_value[:45]}... in {elapsed_time} seconds")

        finally:
            browser.close()

            if self.debug:
                logger.debug(f"Elapsed time: {result.elapsed_time_seconds} seconds")
                logger.debug("Browser closed. Returning result.")

        return result


def get_turnstile_token(url: str, sitekey: str, action: str = None, cdata: str = None, debug: bool = False, headless: bool = False, useragent: str = None, browser_type: str = "chromium", invisible: bool = False) -> Dict:
    """Legacy wrapper function for backward compatibility."""
    browser_types = [
        'chromium',
        'chrome',
        'camoufox',
    ]
    if browser_type not in browser_types:
        logger.error(f"Unknown browser type: {COLORS.get('RED')}{browser_type}{COLORS.get('RESET')} Available browser types: {browser_types}")
    elif headless is True and useragent is None and "camoufox" not in browser_type:
        logger.error(f"You must specify a {COLORS.get('YELLOW')}User-Agent{COLORS.get('RESET')} for Turnstile Solver or use {COLORS.get('GREEN')}camoufox{COLORS.get('RESET')} without useragent")
    else:
        solver = TurnstileSolver(debug=debug, useragent=useragent, headless=headless, browser_type=browser_type)
        result = solver.solve(url=url, sitekey=sitekey, action=action, cdata=cdata, invisible=invisible)
        return result.__dict__


# Credits for the changes: github.com/sexfrance
# Credit for the original script: github.com/Theyka

if __name__ == "__main__":
    result = get_turnstile_token(
        url="https://bypass.city/",
        sitekey="0x4AAAAAAAGzw6rXeQWJ_y2P",
        debug=True,
        invisible=True
    )
    print(result)
