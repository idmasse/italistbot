import gspread
from google.oauth2.service_account import Credentials

# google sheets API setup
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file('utils/gsheet_creds.json', scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("italist tracking").sheet1  # open the first sheet
    return sheet

def batch_gsheet(sheet, orders):
    start_row = len(sheet.get_all_values()) + 1
    data = [[po_num, order_number] for po_num, order_number in orders]
    end_row = start_row + len(data) - 1
    cell_range = f"A{start_row}:B{end_row}"
    sheet.update(cell_range, data)