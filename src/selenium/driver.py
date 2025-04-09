
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Callable
from functools import wraps
import psutil

def with_driver(method) -> Callable:
    """
    Decorator to initialise and close a Selenium driver.

    Parameters
    ----------
    method : Callable
        A method that requires a Selenium driver.

    Returns
    -------
    Callable
        The wrapped method with driver management.
    """
    @wraps(method)
    def wrapper(self,*args,**kwargs):
        self.driver = self._init_driver()
        try:
            return method(self,*args,**kwargs)
        finally:
            self._close_driver()
            self.kill_chromedriver_zombies()
    return wrapper


class ChromeDriverMixin:
    """
    Mixin class to manage Chrome WebDriver initialization and teardown.
    """

    def _init_driver(self, headless:bool = True) -> webdriver.Chrome:
        """
        Initialises a ChromeDriver instance.

        Returns
        -------
        webdriver.Chrome
            The initialized ChromeDriver instance.
        """
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(service=Service(self.driver_path), options=options)
        return driver
    
    def _close_driver(self) -> None:
        """Closes and clears the current Selenium driver."""
        self.driver.quit()
        self.driver = None

    def kill_chromedriver_zombies(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if 'chromedriver' in proc.info['name'].lower():
                try:
                    proc.kill()
                except Exception:
                    pass