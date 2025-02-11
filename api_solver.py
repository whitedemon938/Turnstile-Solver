import asyncio
import time
import json


from typing import Dict, Optional
from dataclasses import dataclass
from patchright.async_api import async_playwright, Page, BrowserContext
from logmagix import Logger, Loader
from quart import Quart, request, jsonify
from collections import deque
from functools import wraps

DEBUG = False

def set_debug(value: bool):
    global DEBUG
    DEBUG = value

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

@dataclass
class TurnstileAPIResult:
    result: Optional[str]
    elapsed_time_seconds: Optional[float] = None
    status: str = "success"
    error: Optional[str] = None

class PagePool:
    def __init__(self, context, debug: bool = False, log=None):
        self.context = context
        self.min_size = 1
        self.max_size = 10
        self.available_pages: deque = deque()
        self.in_use_pages: set = set()
        self._lock = asyncio.Lock()
        self.debug = debug
        self.log = log
        self.max_wait_time = 30  # Maximum time to wait for a page in seconds
        
    async def _cleanup_page(self, page):
        """Reset page state for reuse"""
        try:
            await page.goto("about:blank")
            
            # Clear localStorage if possible
            try:
                await page.evaluate("""() => {
                    try {
                        window.localStorage.clear();
                    } catch (e) {
                        // Ignore security errors
                    }
                }""")
            except Exception:
                pass

            # Clear sessionStorage if possible
            try:
                await page.evaluate("""() => {
                    try {
                        window.sessionStorage.clear();
                    } catch (e) {
                        // Ignore security errors
                    }
                }""")
            except Exception:
                pass

            # Clear cookies
            try:
                await page.context.clear_cookies()
            except Exception:
                pass

        except Exception as e:
            debug(f"Error during page cleanup: {e}")

    async def initialize(self):
        """Create initial pool of pages"""
        for _ in range(self.min_size):
            page = await self.context.new_page()
            self.available_pages.append(page)
        debug(f"Initialized page pool with {self.min_size} pages")

    async def get_page(self):
        """Get an available page from the pool or create a new one if needed"""
        start_time = time.time()
        while True:
            async with self._lock:
                if self.available_pages:
                    page = self.available_pages.popleft()
                    self.in_use_pages.add(page)
                    debug(f"Reusing existing page. Available: {len(self.available_pages)}, In use: {len(self.in_use_pages)}")
                    return page
                
                if len(self.in_use_pages) < self.max_size:
                    page = await self.context.new_page()
                    self.in_use_pages.add(page)
                    debug(f"Created new page. Total pages: {len(self.in_use_pages)}")
                    return page
                
            # If we reach here, we need to wait for a page
            if time.time() - start_time > self.max_wait_time:
                raise TimeoutError("Timeout waiting for available page")
            await asyncio.sleep(0.5)

    async def return_page(self, page):
        """Return a page to the pool after cleanup"""
        async with self._lock:
            if page in self.in_use_pages:
                self.in_use_pages.remove(page)
                
                try:
                    await self._cleanup_page(page)
                    if len(self.available_pages) < self.max_size:
                        self.available_pages.append(page)
                        debug(f"Page returned to pool. Available: {len(self.available_pages)}")
                    else:
                        await page.close()
                        debug("Excess page closed")
                except Exception as e:
                    debug(f"Error returning page to pool: {e}")
                    try:
                        await page.close()
                    except:
                        pass

class BrowserPool:
    def __init__(self, max_browsers=10, debug=False, log=None):
        self.max_browsers = max_browsers
        self.available_browsers: deque = deque()
        self.in_use_browsers: set = set()
        self._lock = asyncio.Lock()
        self.debug = debug
        self.log = log
        self.playwright = None

    async def initialize(self):
        """Initialize the playwright and create initial browser pool"""
        self.playwright = await async_playwright().start()
        for _ in range(self.max_browsers):
            browser = await self._create_browser()
            self.available_browsers.append(browser)
            debug(f"Created browser {_ + 1}/{self.max_browsers}")

    async def _create_browser(self):
        """Create a new browser instance"""
        return await self.playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

    async def get_browser(self):
        """Get an available browser from the pool"""
        async with self._lock:
            while not self.available_browsers:
                await asyncio.sleep(0.1)
            browser = self.available_browsers.popleft()
            self.in_use_browsers.add(browser)
            return browser

    async def return_browser(self, browser):
        """Return a browser to the pool"""
        async with self._lock:
            self.in_use_browsers.remove(browser)
            self.available_browsers.append(browser)

    async def cleanup(self):
        """Close all browsers and cleanup"""
        for browser in list(self.available_browsers) + list(self.in_use_browsers):
            await browser.close()
        if self.playwright:
            await self.playwright.stop()

class TurnstileAPIServer:
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

    def __init__(self, debug: bool = False):
        global DEBUG
        DEBUG = debug
        self.debug = debug
        self.app = Quart(__name__)
        self.log = Logger(github_repository="https://github.com/sexfrance/Turnstile-Solver")
        self.browser_pool = None
        self.page_pools = {}
        self.browser_args = [
            "--disable-blink-features=AutomationControlled",
        ]
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up the application routes."""
        self.app.before_serving(self._startup)
        self.app.route('/turnstile', methods=['GET'])(self.process_turnstile)
        self.app.route('/')(self.index)

    async def _startup(self) -> None:
        """Initialize the browser pool on startup."""
        self.log.debug("Starting browser pool initialization...")
        try:
            self.browser_pool = BrowserPool(
                max_browsers=10,
                debug=self.debug,
                log=self.log
            )
            await self.browser_pool.initialize()
            self.log.success("Browser pool initialized successfully")
        except Exception as e:
            self.log.failure(f"Failed to initialize browser pool: {str(e)}")
            raise

    @debug
    async def _solve_turnstile(self, url: str, sitekey: str, invisible: bool = False, headless: bool = False, cookies: dict = None) -> TurnstileAPIResult:
        """Solve the Turnstile challenge using browser pool."""
        start_time = time.time()
        loader = Loader(desc="Solving captcha...", timeout=0.05)
        loader.start()
        page = None

        try:
            browser = await self.browser_pool.get_browser()
            try:
                if browser not in self.page_pools:
                    self.page_pools[browser] = PagePool(await browser.new_context(), debug=self.debug, log=self.log)
                    await self.page_pools[browser].initialize()
                
                page_pool = self.page_pools[browser]
                page = await page_pool.get_page()
                
                # Rest of the solving logic...
                self.log.debug(f"Starting Turnstile solve for URL: {url}")
                self.log.debug("Setting up page data and route")

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
                        await page.context.add_cookies(cookie_list)

                url_with_slash = url + "/" if not url.endswith("/") else url
                turnstile_div = f'<div class="cf-turnstile" data-sitekey="{sitekey}" data-theme="light"></div>'
                page_data = self.HTML_TEMPLATE.replace("<!-- cf turnstile -->", turnstile_div)

                await page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
                await page.goto(url_with_slash)

                self.log.debug("Starting Turnstile response retrieval loop")

                max_attempts = 10
                attempts = 0
                while attempts < max_attempts:
                    turnstile_check = await page.eval_on_selector(
                        "[name=cf-turnstile-response]", 
                        "el => el.value"
                    )
                    if turnstile_check == "":
                        self.log.debug(f"Attempt {attempts + 1}: No Turnstile response yet")
                        
                        await page.evaluate("document.querySelector('.cf-turnstile').style.width = '70px'")
                        await page.click(".cf-turnstile")
                        await asyncio.sleep(0.5)
                        attempts += 1
                    else:
                        turnstile_element = await page.query_selector("[name=cf-turnstile-response]")
                        if turnstile_element:
                            value = await turnstile_element.get_attribute("value")
                            elapsed_time = round(time.time() - start_time, 3)
                            
                            self.log.debug(f"Turnstile response received: {value[:45]}...")
                            
                            self.log.message(
                                "Cloudflare",
                                f"Successfully solved captcha: {value[:45]}...",
                                start=start_time,
                                end=time.time()
                            )
                            
                            return TurnstileAPIResult(
                                result=value,
                                elapsed_time_seconds=elapsed_time
                            )
                        break

                self.log.failure("Failed to retrieve Turnstile value")
                return TurnstileAPIResult(
                    result=None,
                    status="failure",
                    error="Max attempts reached without solution"
                )

            except Exception as e:
                self.log.failure(f"Error solving Turnstile: {str(e)}")
                return TurnstileAPIResult(
                    result=None,
                    status="error",
                    error=str(e)
                )
            finally:
                if page:
                    await page_pool.return_page(page)
                await self.browser_pool.return_browser(browser)
                loader.stop()
        except Exception as e:
            loader.stop()
            self.log.failure(f"Critical error: {str(e)}")
            return TurnstileAPIResult(
                result=None,
                status="error",
                error=str(e)
            )

    async def process_turnstile(self):
        """Handle the /turnstile endpoint requests."""
        try:
            url = request.args.get('url')
            sitekey = request.args.get('sitekey')
            invisible = request.args.get('invisible', 'false').lower() == 'true'
            
            if not url or not sitekey:
                return jsonify({
                    'status': 'error',
                    'error': 'Missing required parameters: url and sitekey'
                }), 400

            result = await self._solve_turnstile(
                url=url,
                sitekey=sitekey,
                invisible=invisible,
                headless=True
            )
            
            return jsonify({
                'status': result.status,
                'result': result.result,
                'elapsed_time_seconds': result.elapsed_time_seconds,
                'error': result.error
            })

        except Exception as e:
            self.log.failure(f"Error processing turnstile request: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    async def index(self):
        """Serve the API documentation page."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Turnstile Solver API</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 min-h-screen flex items-center justify-center">
            <div class="bg-white p-8 rounded-lg shadow-md max-w-2xl w-full">
                <h1 class="text-3xl font-bold mb-6 text-center text-blue-600">Welcome to Turnstile Solver API</h1>

                <p class="mb-4 text-gray-700">To use the turnstile service, send a GET request to 
                   <code class="bg-gray-200 px-2 py-1 rounded">/turnstile</code> with the following query parameters:</p>

                <ul class="list-disc pl-6 mb-6 text-gray-700">
                    <li><strong>url</strong>: The URL where Turnstile is to be validated</li>
                    <li><strong>sitekey</strong>: The site key for Turnstile</li>
                    <li><strong>invisible</strong>: Optional. Set to true if the Turnstile is invisible.</li>
                </ul>

                <div class="bg-gray-200 p-4 rounded-lg mb-6">
                    <p class="font-semibold mb-2">Example usage:</p>
                    <code class="text-sm break-all">/turnstile?url=https://example.com&sitekey=sitekey&invisible=true</code>
                </div>

                <div class="bg-blue-100 border-l-4 border-blue-500 p-4 mb-6">
                    <p class="text-blue-700">This project is inspired by 
                       <a href="https://github.com/Body-Alhoha/turnaround" class="text-blue-600 hover:underline">Turnaround</a> 
                       and is currently maintained by  <a href="https://github.com/sexfrance" class="text-blue-600 hover:underline">Sexfrance</a>.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def create_app(self):
        """Create and configure the application instance."""
        return self.app

if __name__ == "__main__":
    server = TurnstileAPIServer(debug=True)
    app = server.create_app()
    app.run(host="0.0.0.0")

# Credits for the changes: github.com/sexfrance
# Credit for the original script: github.com/Theyka