from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.selenium_setup import get_driver
from dotenv import load_dotenv
import os
import time

load_dotenv()

def wait_to_click(driver, by, value):
    browser_wait = WebDriverWait(driver, 30)
    return browser_wait.until(EC.element_to_be_clickable((by, value)))

def dismiss_popup(driver):
    browser_wait = WebDriverWait(driver, 5)
    try:
        browser_wait.until(EC.presence_of_element_located((By.ID, 'mcforms-3551-10410')))
        shadow_host = driver.find_element(By.ID, 'mcforms-3551-10410')
        shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
        close_button = shadow_root.find_element(By.ID, 'el_kj1d-fdug3')
        close_button.click()
        print('popup closed')
    except Exception:
        pass

def accept_cookies(driver):
    browser_wait = WebDriverWait(driver, 30)
    try:
        browser_wait.until(EC.presence_of_element_located((By.ID, "usercentrics-cmp-ui")))
        shadow_host = driver.find_element(By.ID, "usercentrics-cmp-ui")
        shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
        accept_button = shadow_root.find_element(By.ID, "accept")
        accept_button.click()
        print('cookie popup accepted')
    except Exception:
        pass

def italist_login(driver, username, password):
    LOGIN_URL = os.getenv('LOGIN_URL')
    driver.get(LOGIN_URL)
    time.sleep(5)

    accept_cookies(driver)
    
    dismiss_popup(driver)
    username_field = wait_to_click(driver, By.XPATH, '/html/body/div[1]/div/div[2]/div[2]/div[1]/form/div[3]/div/div/input')
    username_field.send_keys(username)

    dismiss_popup(driver)
    password_field = wait_to_click(driver, By.XPATH, '//*[@id="root"]/div[2]/div[2]/div[1]/form/div[5]/div/input')
    password_field.send_keys(password)

    dismiss_popup(driver)
    sign_in_btn = wait_to_click(driver, By.XPATH, '//*[@id="root"]/div[2]/div[2]/div[1]/form/div[10]/button')
    sign_in_btn.click()
    time.sleep(3)

    current_url = driver.current_url
    if 'signup' not in current_url:
        return True
    else:
        return False
    
if __name__ == '__main__':
    driver = get_driver()
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    italist_login(driver, username, password)