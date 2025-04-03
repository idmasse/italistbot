import logging
import undetected_chromedriver as uc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

def get_driver():
    logger.info("Initializing undetected Chrome driver...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2
    })
    
    driver = uc.Chrome(options=options)
    logger.info("Undetected Chrome driver initialized successfully.")
    return driver