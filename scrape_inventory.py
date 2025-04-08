import requests
import os
from utils.ftp_utils import connect_ftp, upload_files
from dotenv import load_dotenv

load_dotenv()

inventory_file_url = os.getenv('INVENTORY_URL')

local_filename = 'inventory.csv'

def scrape_inventory():
    try:
        print('downloading inventory file from s3 bucket')
        response = requests.get(inventory_file_url)
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            f.write(response.content)
        print(f"file downloaded and saved locally as {local_filename}")
    except Exception as e:
        print(f"failed to download file: {e}")

    ftp = connect_ftp()
    if not ftp:
        print("failed to connect to FTP")

    # upload the file to the inventory directory on the FTP server
    try:
        print('uploading file to ftp server')
        upload_files(ftp, local_file_path=local_filename, remote_file_name=local_filename)
        print(f"file uploaded to ftp: /in/inventory/{local_filename}")
    finally:
        ftp.quit()
