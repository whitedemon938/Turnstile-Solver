import os
import sys
import time
import random
import string
import logging
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from camoufox.async_api import AsyncCamoufox
from patchright.async_api import async_playwright


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


class AsyncTurnstileSolver:
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
        self.browser_args = []
        if useragent:
            self.browser_args.append(f"--user-agent={useragent}")

    async def _setup_page(self, browser, url: str, sitekey: str, action: str = None, cdata: str = None):
        """Set up the page with Turnstile widget."""
        if self.browser_type == "chrome":
            page = browser.pages[0]
        else:
            page = await browser.new_page()

        url_with_slash = url + "/" if not url.endswith("/") else url

        turnstile_div = f'<div class="cf-turnstile" data-sitekey="{sitekey}"' + (f' data-action="{action}"' if action else '') + (f' data-cdata="{cdata}"' if cdata else '') + '></div>'
        page_data = self.HTML_TEMPLATE.replace("<!-- cf turnstile -->", turnstile_div)

        if self.debug:
            logger.debug(f"Starting Turnstile solve for URL: {url} with Sitekey: {sitekey}")

        await page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
        await page.goto(url_with_slash)

        return page

    async def _get_turnstile_response(self, page, max_attempts: int = 10) -> Optional[str]:
        """Attempt to retrieve Turnstile response."""
        for _ in range(max_attempts):
            turnstile_check = await page.eval_on_selector(
                "[name=cf-turnstile-response]",
                "el => el.value"
            )

            if turnstile_check == "":
                if self.debug:
                    logger.debug(f"Attempt {_+1}: No Turnstile response yet.")

                await page.evaluate("document.querySelector('.cf-turnstile').style.width = '70px'")
                await page.click(".cf-turnstile")
                await asyncio.sleep(0.5)
            else:
                turnstile_element = await page.query_selector("[name=cf-turnstile-response]")
                if turnstile_element:
                    return await turnstile_element.get_attribute("value")
                break

        return None

    async def solve(self, url: str, sitekey: str, action: str = None, cdata: str = None) -> TurnstileResult:
        """
        Solve the Turnstile challenge and return the result.
        """
        start_time = time.time()
        if self.browser_type == "chromium":
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=self.browser_args
            )

        elif self.browser_type == "chrome":
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=f"{os.getcwd()}/tmp/turnstile-chrome-{''.join(random.choices(string.ascii_letters + string.digits, k=10))}",
                channel="chrome",
                headless=self.headless,
                no_viewport=True,
            )

        elif self.browser_type == "camoufox":
            browser = await AsyncCamoufox(headless=self.headless).start()

        try:
            page = await self._setup_page(browser, url, sitekey, action, cdata)
            turnstile_value = await self._get_turnstile_response(page)

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
            await browser.close()
            if self.browser_type == "chrome" or self.browser_type == "chromium":
                await playwright.stop()
            else:
                try:
                    await browser.stop()
                except:
                    pass

            if self.debug:
                logger.debug(f"Elapsed time: {result.elapsed_time_seconds} seconds")
                logger.debug("Browser closed. Returning result.")

        return result


async def get_turnstile_token(url: str, sitekey: str, action: str = None, cdata: str = None, debug: bool = False, headless: bool = False, useragent: str = None, browser_type: str = "chromium") -> Dict:
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
        solver = AsyncTurnstileSolver(debug=debug, useragent=useragent, headless=headless, browser_type=browser_type)
        result = await solver.solve(url=url, sitekey=sitekey, action=action, cdata=cdata)
        return result.__dict__


if __name__ == "__main__":
    result = asyncio.run(get_turnstile_token(
        url="https://bypass.city/",
        sitekey="0x4AAAAAAAGzw6rXeQWJ_y2P",
        action=None,
        cdata=None,
        debug=True,
        headless=False,
        useragent=None,
        browser_type="camoufox"
    ))
    print(result)
