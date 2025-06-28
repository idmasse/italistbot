from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from utils.ftp_utils import connect_ftp, download_files, archive_files_on_ftp
from utils.gsheet_setup import setup_google_sheets, batch_gsheet
from utils.selenium_setup import get_driver
from utils.sql_utils import get_product_url
from utils.email_utils import send_email
from login import italist_login, dismiss_popup
from scrape_inventory import scrape_inventory
from dotenv import load_dotenv
import shutil
import csv
import time
import os, sys

load_dotenv()

def add_variant_param(url: str, sku: str) -> str:
    q_index = url.find('?')
    if q_index == -1:
        return f"{url}?variant={sku}"
    else:
        return url[:q_index+1] + f"variant={sku}&" + url[q_index+1:]
    
def main():
    #setup sheets and batch sheet updates
    sheet = setup_google_sheets()
    orders_to_update = []

    try:
        #track success/failure
        successful_orders = []
        failed_orders = []

        #setup local archive directory
        archive_dir = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), 'processed')
        os.makedirs(archive_dir, exist_ok=True)

        # download order files from the ftp
        ftp = connect_ftp()
        downloaded_files = []
        if ftp:
            try:
                downloaded_files = download_files(ftp)
            finally:
                if downloaded_files:
                    archive_files_on_ftp(ftp, downloaded_files)
                ftp.quit()
                print('FTP connection closed')
        else:
            print("could not connect to FTP")
            return
        
        if not downloaded_files:
            print('no files to download, quitting')
            return
        
        # process each file loop
        for file in downloaded_files:
            try:
                file_path = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), file)
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    orders_data = list(reader)
        
                # group orders by PO_num
                grouped_orders = {}
                for row in orders_data:
                    po_key = [key for key in row.keys() if 'PO_num' in key][0]
                    po_num = row[po_key]
                    if po_num not in grouped_orders:
                        grouped_orders[po_num] = {
                            'shipping_info': {
                                'fname': row['First Name'],
                                'lname': row['Last Name'],
                                'address1': row['Ship To Address'],
                                'address2': row.get('Ship To Address 2', ''),
                                'city': row['Ship To City'],
                                'state': row['Ship To State'],
                                'zip': row['Ship To Zip']
                            },
                            'items': []
                        }
                    grouped_orders[po_num]['items'].append({
                        'sku': row['SKU'],
                        'quantity': row['Qty']
                    })

                # Setup batching
                batch_size = 15
                orders = list(grouped_orders.items())
                po_nums = [po for po, _ in orders]
                print(f'Processing orders: {po_nums}')

                # Process in batches 
                for i in range(0, len(orders), batch_size):
                    current_batch = orders[i:i+batch_size]
                    print(f'Processing batch {i//batch_size + 1}: {[po for po, _ in current_batch]}')
                    
                    driver = get_driver()
                    try:
                        username = os.getenv('USERNAME')
                        password = os.getenv('PASSWORD')
                        login_success = italist_login(driver, username, password)
                        if not login_success:
                            print("Login failed, skipping batch")
                            driver.quit()
                            continue

                        # selenium shortcuts
                        browser_wait = WebDriverWait(driver, 30)
                        def click_wait(by, value, browser_wait=browser_wait):
                            return browser_wait.until(EC.element_to_be_clickable((by, value)))
                                        
                        def el_wait(by, value, browser_wait=browser_wait):
                            return browser_wait.until(EC.presence_of_element_located((by, value)))   
                        
                        for po_num, order in current_batch:
                            try:
                                print(f'Processing PO_num: {po_num}')
                                
                                try:
                                    print('emptying shopping cart if necessary')
                                    dismiss_popup(driver)
                                    driver.get('https://www.italist.com/us/cart')
                                    time.sleep(3)
                                
                                    remove_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='cart-remove-item-button']")
                                    if remove_buttons:
                                        print(f'found {len(remove_buttons)} items in cart - removing all items')
                                        for remove_btn in remove_buttons:
                                            remove_btn.click()
                                            time.sleep(1)
                                except Exception as e:
                                    print(f'error clicking remove button: {e}')

                                item_urls = {}
                                
                                # First, verify all URLs exist
                                missing_url = False
                                
                                for item in order['items']:
                                    sku = item['sku']
                                    print(f'Looking up URL for SKU: {sku}')
                                    url = get_product_url(sku)
                                    
                                    if not url:
                                        print(f'No URL found for SKU: {sku}')
                                        missing_url = True
                                        failed_orders.append((file, po_num, f'missing url for {sku}'))
                                        break
                                    
                                    # Store URL for later use
                                    item_urls[sku] = add_variant_param(url, sku)
                                    print(f'Found variant URL: {item_urls[sku]}')
                                
                                # If any URL is missing, skip this PO
                                if missing_url:
                                    print(f'Skipping PO {po_num} due to missing URL')
                                    continue
                                
                                # Now process all items with their cached URLs
                                for item in order['items']:
                                    sku = item['sku']
                                    quantity = item['quantity']
                                    
                                    # Use the cached URL
                                    variant_url = item_urls[sku]
                                    
                                    print(f'Navigating to product variant URL for {sku}')
                                    driver.get(variant_url)
                                    time.sleep(2)

                                    product_page = el_wait(By.CLASS_NAME, 'product-info-card')
                                    if product_page:
                                        print('Product page loaded')
                                    else:
                                        el_wait(By.CLASS_NAME, 'product-info-card')

                                    print('Adding item to cart')
                                    add_to_bag_btn = click_wait(By.CLASS_NAME, 'jsx-2719816334')
                                    add_to_bag_btn.click()
                                    time.sleep(3)

                                    if int(quantity) > 1:
                                        print(f'Setting quantity to: {quantity}')
                                        additional_clicks = int(quantity) - 1
                                        
                                        for _ in range(additional_clicks):
                                            quant_btn = click_wait(By.CLASS_NAME, 'icon-plus')
                                            quant_btn.click()
                                            time.sleep(0.5)

                                print(f"Finished adding all items for PO_num {po_num}")

                                # Checkout process for this PO
                                print(f"Starting checkout for PO_num {po_num}")
                                checkout_btn = click_wait(By.CLASS_NAME, 'jsx-838475951')
                                checkout_btn.click()
                                
                                shipping_info = order["shipping_info"]
                                click_wait(By.CLASS_NAME, 'c-shipping')

                                print('filling shipping fields')
                                fields = {
                                    'firstName': shipping_info['fname'],
                                    'lastName': shipping_info['lname'],
                                    'addressLine1': shipping_info['address1'],
                                    'addressLine2': shipping_info['address2'],
                                    'city': shipping_info['city'],
                                    'postalCode': shipping_info['zip']
                                }
                                    
                                for field_id, value in fields.items():
                                    field = click_wait(By.NAME, field_id)
                                    field.clear()
                                    field.send_keys(value)
                                    time.sleep(0.5)

                                print('selecting state from dropdown')
                                state_to_select = shipping_info['state']
                                state_dropdown = click_wait(By.CSS_SELECTOR, ".c-form-select__value-container.c-form-select__value-container--has-value.css-hlgwow")
                                state_dropdown.click()

                                state_option_locator = (By.XPATH, f"//div[contains(@class, 'c-form-select__option') and normalize-space()='{state_to_select}']")
                                state_option = el_wait(*state_option_locator)
                                state_option.click()

                                print('clicking first continue button')
                                checkout_continue_btn1 = click_wait(By.CLASS_NAME, 'jsx-306009241')
                                checkout_continue_btn1.click()

                                print('inputting discount code')
                                discount_code_btn = click_wait(By.CLASS_NAME, 'c-chevron-button')
                                discount_code_btn.click()
                                discount_input = click_wait(By.XPATH, '//*[@id="__next"]/div/main/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/input')
                                DISCOUNT_CODE = os.getenv('DISCOUNT_CODE')
                                discount_input.send_keys(DISCOUNT_CODE)
                                discount_input_btn = click_wait(By.CSS_SELECTOR, '.jsx-2057648303.button')
                                discount_input_btn.click()
                                time.sleep(2) #wait for page refresh after discount input

                                print('clicking second continue button')
                                continue_to_payment_btn = click_wait(By.CLASS_NAME, 'jsx-306009241')
                                continue_to_payment_btn.click()
                                time.sleep(5) #wait for payment box to load

                                # CC security code input in iframe
                                print('filling CVV code')
                                iframe = driver.find_element(By.CLASS_NAME, 'js-iframe')
                                driver.switch_to.frame(iframe)
                                cvv_input = click_wait(By.CSS_SELECTOR, '.js-iframe-input.input-field')
                                cvv_input.clear()
                                cvv_input.send_keys(os.getenv('CVV'))
                                driver.switch_to.default_content()

                                #submit the order
                                print('submitting the order')
                                submit_order_btn = click_wait(By.CLASS_NAME, 'adyen-checkout__button--pay')
                                submit_order_btn.click()
                                time.sleep(5)

                                # verify order confirmation
                                print('waiting for confirmation')
                                order_confirmation = el_wait(By.CLASS_NAME, 'c-thank-you-page__title')
                                print(f'confirmation found: {order_confirmation.text}')
                                print(f'{po_num} processed successfully')

                                #get the order number
                                italist_order_msg = driver.find_element(By.XPATH, '//*[@id="__next"]/div/main/div[1]/div[3]/div[2]/div[2]')
                                italist_order_num = italist_order_msg.text
                                print(f'found order number: {italist_order_num}')

                                orders_to_update.append((po_num, italist_order_num))
                                print(f'added {po_num} and {italist_order_num} to gsheet batch')

                                # after checkout is complete, mark order as successful
                                successful_orders.append((file, po_num))
                                print(f"Successfully processed order {po_num}")

                                time.sleep(5)
                            except Exception as e:
                                print(f"error during checkout for {po_num}: {e}")
                                failed_orders.append((file, po_num, str(e)))

                    except Exception as e:
                        print(f"Error processing file {file}: {e}")  
            
                    finally:
                        if driver:
                            driver.quit()
                            print('driver closed')

            except Exception as e:
                print(f'failed to process file: {file} with error: {e}')
        
        print(f'successfully processed file: {file}')

        # update google sheet with batch info
        if orders_to_update:
            batch_gsheet(sheet, orders_to_update)
            print('successfully updated batch orders to gsheet')
        
        # archive the local files
        for file in downloaded_files:
            src = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), file)
            dst = os.path.join(archive_dir, file)
            try:
                shutil.move(src, dst)
                print(f"moved {file} to archive")
            except Exception as e:
                print(f"failed to move {file}: {str(e)}")
        
        # send summary email
        print('sending summary email')
        subject = "Italist Order Summary"
        successful_msg = ', '.join(f'{po_num} ({f})' for f, po_num in successful_orders) if successful_orders else "None"
        failed_msg = ', '.join(f'{po_num} ({f})' for f, po_num, _ in failed_orders) if failed_orders else "None"

        body = f"""
        Successful orders: {len(successful_orders)}
        {successful_msg}

        Failed orders: {len(failed_orders)}
        {failed_msg}"""

        send_email(subject, body)
        
    except Exception as e:
        send_email('Italist Bot Failed', f'Italist Bot failed with error: {str(e)}')

if __name__ == '__main__':
    main()
    scrape_inventory()