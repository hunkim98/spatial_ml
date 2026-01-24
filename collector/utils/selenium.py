from selenium import webdriver
import logging
import random
import os
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SeleniumUtil:
    """
    Utility class to manage a single Selenium WebDriver instance.
    Uses a virtual display (Xvfb) for running Chrome in non-headless mode in Docker/Vertex AI.
    Use the 'driver' property to access the current WebDriver from anywhere this util is used.
    """

    # List of realistic user agents to rotate through
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, headless: bool = False, logger: logging.Logger = None, download_dir: str = None):
        """
        Initialize SeleniumUtil.

        Args:
            headless: If False (default), uses virtual display for compatibility with Next.js sites.
                     If True, uses headless Chrome (may not work with some sites).
            logger: Logger instance.
            download_dir: Directory for downloads.
        """
        self.headless = headless
        self.logger = logger or logging.getLogger(__name__)
        self.download_dir = download_dir
        self._driver = None
        self._display = None
        self.current_user_agent = None

    def _start_virtual_display(self):
        """Start a virtual display for running Chrome in non-headless mode."""
        if self._display is not None:
            return

        try:
            from pyvirtualdisplay import Display
            # Use Xvfb backend explicitly
            self._display = Display(visible=False, size=(1920, 1080), backend="xvfb")
            self._display.start()
            self.logger.info(f"Virtual display started (Xvfb) on DISPLAY={os.environ.get('DISPLAY', 'not set')}")
        except Exception as e:
            self.logger.warning(f"Could not start virtual display: {e}. Falling back to headless mode.")
            self.headless = True

    def _stop_virtual_display(self):
        """Stop the virtual display."""
        if self._display:
            try:
                self._display.stop()
                self.logger.info("Virtual display stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping virtual display: {e}")
            self._display = None

    @property
    def driver(self):
        """
        Returns a managed driver instance, initializing if not already created.
        """
        if self._driver is None:
            self.initialize_driver()
        return self._driver

    def initialize_driver(self):
        # Start virtual display if not using headless mode
        if not self.headless:
            self._start_virtual_display()

        # Select a random user agent
        self.current_user_agent = random.choice(self.USER_AGENTS)
        self.logger.info(f"Using User-Agent: {self.current_user_agent[:50]}...")
        self.logger.info(f"Headless mode: {self.headless}, DISPLAY={os.environ.get('DISPLAY', 'not set')}")

        chrome_options = Options()

        if self.headless:
            # Use older headless mode for better compatibility
            chrome_options.add_argument("--headless=chrome")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(f"--user-agent={self.current_user_agent}")

        # Configure download directory if specified
        if self.download_dir:
            import json
            os.makedirs(self.download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "safebrowsing.enabled": True,
                "printing.print_preview_sticky_settings.appState": json.dumps({
                    "recentDestinations": [{
                        "id": "Save as PDF",
                        "origin": "local",
                        "account": "",
                    }],
                    "selectedDestinationId": "Save as PDF",
                    "version": 2,
                    "isHeaderFooterEnabled": False,
                    "isLandscapeEnabled": False,
                    "isCssBackgroundEnabled": True,
                })
            }
            chrome_options.add_experimental_option("prefs", prefs)

        # ChromeDriver is installed via base image
        self._driver = webdriver.Chrome(options=chrome_options)
        self.logger.info(f"Chrome WebDriver initialized (headless={self.headless})")

        # Enable downloads in headless mode
        if self.headless and self.download_dir:
            try:
                self._driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {
                        "behavior": "allow",
                        "downloadPath": self.download_dir,
                    }
                )
                self.logger.info(f"Enabled downloads to: {self.download_dir}")
            except Exception as e:
                self.logger.warning(f"Could not enable downloads: {e}")

        return self._driver

    def find_element(self, by, value, timeout: int = 10):
        """
        Finds an element on the page.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def find_elements(self, by, value, timeout: int = 10):
        """
        Finds elements on the page.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )

    def click_element(self, by, value, timeout: int = 10):
        """
        Clicks an element on the page.
        """
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()

    def wait_for_element(self, by, value, timeout: int = 10):
        """
        Waits for an element to be present and visible.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def reinitialize_with_new_headers(self):
        """
        Reinitialize the driver with a new random user agent.
        Useful for avoiding detection when making many requests.
        """
        self.logger.info("Reinitializing driver with new headers...")
        self.quit()
        self.initialize_driver()
        return self._driver

    def quit(self):
        """
        Cleanly shuts down the driver if it's running.
        """
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info("Chrome WebDriver has been quit.")
            except Exception as e:
                self.logger.warning(f"Error quitting Chrome WebDriver: {e}")
            self._driver = None

        # Stop virtual display
        self._stop_virtual_display()

    def __del__(self):
        # Ensure driver is closed if the util is garbage collected
        self.quit()
