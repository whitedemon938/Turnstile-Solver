import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from patchright.async_api import async_playwright, Page, BrowserContext
from logmagix import Logger, Loader
from functools import wraps

def debug(func_or_message, *args, **kwargs):
    global DEBUG
    if callable(func_or_message):
        @wraps(func_or_message)
        async def wrapper(*args, **kwargs):
            result = await func_or_message(*args, **kwargs)
            if DEBUG:
                Logger().debug(f"{func_or_message.__name__} returned: {result}")
            return result
        return wrapper
    else:
        if DEBUG:
            Logger().debug(f"Debug: {func_or_message}")

@dataclass
class TurnstileResult:
    turnstile_value: Optional[str]
    elapsed_time_seconds: float
    status: str
    reason: Optional[str] = None

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

    def __init__(self, debug: bool = False, headless: Optional[bool] = False, useragent: Optional[str] = None):
        global DEBUG
        DEBUG = debug
        self.debug = debug
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

        if self.useragent:
            self.browser_args.append(f"--user-agent={self.useragent}")

    @debug
    async def _setup_page(self, context: BrowserContext, url: str, sitekey: str = None) -> Page:
        """Set up the page with or without Turnstile widget."""
        page = await context.new_page()
        url_with_slash = url + "/" if not url.endswith("/") else url

        debug(f"Navigating to URL: {url_with_slash}")

        if sitekey:
            turnstile_div = f'<div class="cf-turnstile" data-sitekey="{sitekey}" data-theme="light"></div>'
            page_data = self.HTML_TEMPLATE.replace("<!-- cf turnstile -->", turnstile_div)
            await page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
        
        await page.goto(url_with_slash)
        return page

    @debug
    async def _get_turnstile_response(self, page: Page, max_attempts: int = 10, invisible: bool = False) -> Optional[str]:
        """Attempt to retrieve Turnstile response."""
        attempts = 0

        while attempts < max_attempts:
            turnstile_check = await page.eval_on_selector(
                "[name=cf-turnstile-response]", 
                "el => el.value"
            )

            if turnstile_check == "":
                debug(f"Attempt {attempts + 1}: No Turnstile response yet.")

                if not invisible:
                    await page.evaluate("document.querySelector('.cf-turnstile').style.width = '70px'")
                    await page.click(".cf-turnstile")

                await asyncio.sleep(0.5)
                attempts += 1
            else:
                turnstile_element = await page.query_selector("[name=cf-turnstile-response]")
                if turnstile_element:
                    return await turnstile_element.get_attribute("value")
                break

        return None

    async def solve(self, url: str, sitekey: str = None, invisible: bool = False, cookies: dict = None) -> TurnstileResult:
        """
        Solve the Turnstile challenge and return the result.
        
        Args:
            url: The URL where the Turnstile challenge is hosted
            sitekey: The Turnstile sitekey
            headless: Whether to run the browser in headless mode
            invisible: Whether the Turnstile challenge is invisible
            cookies: Optional dictionary of cookies to set

        Returns:
            TurnstileResult object containing the solution details
        """
        self.loader.start()
        start_time = time.time()

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=self.headless, args=self.browser_args)
                context = await browser.new_context()

                if cookies:
                    domain = url.split("//")[-1].split("/")[0]
                    cookie_list = []
                    for name, value in cookies.items():
                        cookie_list.append({
                            "name": name,
                            "value": str(value),
                            "domain": domain,
                            "path": "/"
                        })
                    if cookie_list:
                        await context.add_cookies(cookie_list)

                try:
                    page = await self._setup_page(context, url, sitekey)
                    turnstile_value = await self._get_turnstile_response(page, invisible=invisible)

                    elapsed_time = round(time.time() - start_time, 3)

                    if not turnstile_value:
                        result = TurnstileResult(
                            turnstile_value=None,
                            elapsed_time_seconds=elapsed_time,
                            status="failure",
                            reason="Max attempts reached without token retrieval"
                        )
                        self.log.failure("Failed to retrieve Turnstile value.")
                    else:
                        result = TurnstileResult(
                            turnstile_value=turnstile_value,
                            elapsed_time_seconds=elapsed_time,
                            status="success"
                        )
                        self.loader.stop()
                        self.log.message(
                            "Cloudflare",
                            f"Successfully solved captcha: {turnstile_value[:45]}...",
                            start=start_time,
                            end=time.time()
                        )

                except Exception as e:
                    self.log.failure(f"Error during captcha solving: {str(e)}")
                    raise

                finally:
                    try:
                        await context.close()
                        await browser.close()
                    except Exception as e:
                        self.log.failure(f"Error closing browser: {str(e)}")
                    
                        debug(f"Elapsed time: {result.elapsed_time_seconds} seconds")
                        debug("Browser closed. Returning result.")

        except Exception as e:
            elapsed_time = round(time.time() - start_time, 3)
            self.loader.stop()
            return TurnstileResult(
                turnstile_value=None,
                elapsed_time_seconds=elapsed_time,
                status="error",
                reason=str(e)
            )

        return result

@debug
async def get_turnstile_token(headless: bool = False, url: str = None, sitekey: str = None, invisible: bool = False, cookies: dict = None, user_agent: str = None, debug: bool = True) -> Dict:
    """Legacy wrapper function for backward compatibility."""
    solver = AsyncTurnstileSolver(headless=headless, useragent=user_agent, debug=debug)
    result = await solver.solve(url=url, sitekey=sitekey, invisible=invisible, cookies=cookies)
    return result.__dict__

if __name__ == "__main__":
    async def main():
        result = await get_turnstile_token(
            url="https://streamlabs.com",
            sitekey="0x4AAAAAAACELUBpqiwktdQ9",
            invisible=True
        )
        print(result)

    asyncio.run(main())

# Credits for the changes: github.com/sexfrance
# Credit for the original script: github.com/Theyka
