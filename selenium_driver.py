from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


# --------------------------------------------------------
# OPTIMIZED CHROME OPTIONS
# --------------------------------------------------------
def get_optimized_chrome_options(headless=False):
    options = Options()

    # ---- HEADLESS MODE (new 2023+ version) ----
    if headless:
        options.add_argument("--headless=new")

    # ---- PERFORMANCE ----
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # ---- SPEED OPTIMIZATION ----
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # No images, no css, no fonts → much faster
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.media_stream": 2,
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    # ---- AVOID DETECTION ----
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # ---- STABILITY ----
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")

    return options


# --------------------------------------------------------
# SELENIUM DRIVER CLASS
# --------------------------------------------------------
class SeleniumDriver:
    def __init__(self, headless=False, timeout=15):
        """Initialize driver with optimized options."""
        # chrome_options = get_optimized_chrome_options(headless)
        service = Service()

        # self.driver = webdriver.Chrome(service=service, options=chrome_options)
        #self.driver = webdriver.Chrome(service=service)
        self.driver= webdriver.Chrome()
        #self.wait = WebDriverWait(self.driver, timeout)

        
        

    def get(self, url):
        self.driver.get(url)
    

    def close(self):
        self.driver.quit()
