import logging
import random
from playwright.sync_api import sync_playwright, Page, Browser


class PlaywrightUtil:
    """
    Utility class to manage Playwright browser instance with stealth mode.
    Better compatibility with Next.js and bot-protected sites than Selenium headless.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, headless: bool = True, logger: logging.Logger = None):
        self.headless = headless
        self.logger = logger or logging.getLogger(__name__)
        self._playwright = None
        self._browser: Browser = None
        self._page: Page = None
        self.current_user_agent = None

    @property
    def page(self) -> Page:
        """Returns the managed page instance, initializing if needed."""
        if self._page is None:
            self.initialize()
        return self._page

    def initialize(self):
        """Initialize Playwright browser and page."""
        self.current_user_agent = random.choice(self.USER_AGENTS)
        self.logger.info(f"Using User-Agent: {self.current_user_agent[:50]}...")

        self._playwright = sync_playwright().start()

        # Launch browser with stealth settings
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        # Create context with realistic settings
        context = self._browser.new_context(
            user_agent=self.current_user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            # Stealth settings
            java_script_enabled=True,
            bypass_csp=True,
        )

        # Add stealth scripts
        context.add_init_script("""
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Add chrome object
            window.chrome = {runtime: {}};

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        self._page = context.new_page()
        self.logger.info(f"Playwright browser initialized (headless={self.headless})")

    def goto(self, url: str, wait_until: str = "networkidle", timeout: int = 30000):
        """Navigate to URL and wait for page load."""
        self.page.goto(url, wait_until=wait_until, timeout=timeout)

    def wait_for_selector(self, selector: str, timeout: int = 10000):
        """Wait for element to be present."""
        return self.page.wait_for_selector(selector, timeout=timeout)

    def query_selector_all(self, selector: str):
        """Find all elements matching selector."""
        return self.page.query_selector_all(selector)

    def query_selector(self, selector: str):
        """Find single element matching selector."""
        return self.page.query_selector(selector)

    def click(self, selector: str, timeout: int = 10000):
        """Click element."""
        self.page.click(selector, timeout=timeout)

    def get_text_content(self, selector: str) -> str:
        """Get text content of element."""
        element = self.page.query_selector(selector)
        return element.text_content() if element else ""

    def get_attribute(self, selector: str, attribute: str) -> str:
        """Get attribute value of element."""
        element = self.page.query_selector(selector)
        return element.get_attribute(attribute) if element else ""

    @property
    def title(self) -> str:
        """Get page title."""
        return self.page.title()

    @property
    def content(self) -> str:
        """Get page content (HTML)."""
        return self.page.content()

    def reinitialize(self):
        """Reinitialize browser with new user agent."""
        self.logger.info("Reinitializing Playwright browser...")
        self.quit()
        self.initialize()

    def quit(self):
        """Close browser and playwright."""
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None

        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self.logger.info("Playwright browser closed")

    def __del__(self):
        self.quit()
