import requests
from requests import request
import json
import time
import sys
from urllib.parse import quote

# config
# get from google cloud account CLIENT_ID_GS = 
# get from google cloud account CLIENT_SECRET_GS = 
# get from output refresh token script REFRESH_TOKEN_GS = 
# ID from googlesheet link SID = 

#DK variables
# https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id=<fill>&redirect_uri=https://localhost
code = ''  # CODE TO INITIATE AUTH
token_filename = 'digi_token.json'
test_partnumber = 'BSS138'

# constants
SPACE = " "

def get_access_token(auth_code, filename):
    token = load_token_from_file(filename)
    url = 'https://api.digikey.com/v1/oauth2/token'
    url_data = {
        'code': auth_code,
        'client_id': token['client_id'],
        'client_secret': token['client_secret'],
        'redirect_uri': 'https://localhost',
        'grant_type': 'authorization_code'
    }
    response = requests.post(url, data=url_data)
    print(response.status_code)
    print(token)
    print(response)
    print(response.json())
    print(response.reason)

    if response.status_code == 200:
        print('\033[32mAccess Token get SUCCESS\033[0m')
        response_data = response.json()
        token['access_token'] = response_data['access_token']
        token['refresh_token'] = response_data['refresh_token']
        token['expires_in'] = response_data['expires_in']
        token['refresh_token_expires_in'] = response_data['refresh_token_expires_in']
        token['token_type'] = response_data['token_type']

    with open(filename, "w") as f:
        json.dump(token, f)

    return (response.json())

#Only at first time to activate token
#get_access_token(code, token_filename)

def load_token_from_file(filename):
    with open(filename, 'r') as f:
        token = json.load(f)

    if token != False:
        print('\033[32mToken load SUCCESS.\033[0m')
    else:
        print('\033[31m\033[1mToken load FAILED.\033[0m')
    return token


def get_refresh_token(token, filename):
    url = 'https://api.digikey.com/v1/oauth2/token'

    if token == False:
        return False

    url_data = {
        'client_id': token['client_id'],
        'client_secret': token['client_secret'],
        'refresh_token': token['refresh_token'],
        'grant_type': 'refresh_token'
    }

    response = requests.post(url, data=url_data)

    if response.status_code == 200:
        print('\033[32mToken refresh SUCCESS\033[0m')
        response_data = response.json()

        token['refresh_token_time'] = time.time()
        token['access_token'] = response_data['access_token']
        token['refresh_token'] = response_data['refresh_token']
        token['expires_in'] = response_data['expires_in']
        token['refresh_token_expires_in'] = response_data['refresh_token_expires_in']
        token['token_type'] = response_data['token_type']

        with open(filename, "w") as arquivo:
            json.dump(token, arquivo)
    else:
        print('\033[31m\033[1mToken refreshed FAILED\033[0m')
        print(response.status_code)
        print(response.reason)

    if response:
        return (token)
    else:
        return False

#print('\033[31mLoading token from file: \033[0m')
token = load_token_from_file('digi_token.json')

#print('\033[31mRefreshing token: \033[0m')
token_refreshed = get_refresh_token(token, token_filename)

''' Given the refresh token, return the response which includes the access
    token and other bits of information.
'''
def refresh_access_token(refresh_tkn):
    url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID_GS,
        "client_secret": CLIENT_SECRET_GS,
        "refresh_token": refresh_tkn
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }

    r = request("POST", url, data=data, headers=headers)
    return r

''' Given a string message, row index and column index, return the payload of
    a cell.
'''

def a_cell(message, row, col):
    if isinstance(message, (int, float)):
        value = {"numberValue": float(message)}
    else:
        value = {"stringValue": str(message)}

    cell = {
        "updateCells": {
            "rows": [
                {
                    "values": [
                        {
                                #"numberValue": message
                                #"stringValue": message
                                "userEnteredValue": value
                        }
                    ]
                }
            ],
            "fields": "userEnteredValue",
            "start": {
                "sheetId": 0,
                "rowIndex": row,
                "columnIndex": col
            }
        }
    }
    return cell

''' Generate the request with the default intention of filling the entire row
    at `index` with the list of messages. If `row_fill` is set to `False`, 
    the column at `index` will be filled instead.
'''

def generate_request(messages, index, row_fill):
    #requests.append(a_cell(messages,4,4))

    #Zabezpieczenie zeby przesyłała sie cena jako pojedynczy arg
    if not isinstance(messages, (list, tuple)):
        messages = [messages]

    requests = []

    if row_fill:
        for i in range(len(messages)):
            requests.append(a_cell(messages[i], index, i+3))
    # column fill
    else:
        for i in range(len(messages)):
            requests.append(a_cell(messages[i], i, index))
    return requests
'''
class gsheets_get():

    def __init__(self, refresh_tkn):
        r = refresh_access_token(refresh_tkn)
        data = r.json()
        self.token = data["access_token"]
        self.token_type = data["token_type"]'''


def get_product_details(partnumber, token):
    partnumber_quoted = partnumber.replace('/', '%2F')
    partnumber_quoted = partnumber_quoted.replace('+', '%2B')
    partnumber_quoted = partnumber_quoted.replace('#', '%23')
    url = f'https://api.digikey.com/Search/v3/Products/{partnumber_quoted}'
    url2 = f'"https://www.digikey.com/en/products/result?keywords={partnumber_quoted}'
    print(url2)
    # print(url)

    url_header = {
        'x-digikey-locale': 'pt',
        'X-DIGIKEY-Locale-Site': 'BR',
        'X-DIGIKEY-Locale-Currency': 'BRL',
        'Authorization': f"{token['token_type']} {token['access_token']}",
        'X-DIGIKEY-Client-Id': token['client_id']
    }

    response = requests.get(url, headers=url_header)

    if response.status_code == 200:
        response_dict = response.json()
        print(f'\033[32mGot information for {partnumber}\033[0m')
        return response_dict
    else:
        print(f'\033[31mFailed to get information for {partnumber}\033[0m')
        print(response.status_code, response.reason)
        return False


def get_product_unit_price(partnumber, token):
    response_dict = get_product_details(partnumber, token)
    if response_dict == False:
        print(f'\033[31m\033[1mFailed to fetch PN price: {partnumber}\033[0m')
        return 0
    else:
        try:
            price = response_dict['StandardPricing'][0]['UnitPrice']
            return price
        except:
            return 0


class gsheets():

    def __init__(self, refresh_tkn):  #mozna dodać odwołanie do funkcji spoza klasy
        r = refresh_access_token(refresh_tkn)
        data = r.json()
        self.token = data["access_token"]
        self.token_type = data["token_type"]

    def update_cells(self, messages, index, spreadsheet_id, row_fill=True):
        url = "https://sheets.googleapis.com/v4/spreadsheets/" \
              + f"{spreadsheet_id}:batchUpdate"

        body = {
            "requests": [],
            "includeSpreadsheetInResponse": False,
            "responseRanges": [],
            "responseIncludeGridData": False
        }

        if row_fill:
            body["requests"] = generate_request(messages, index, row_fill=True)
        else:
            body["requests"] = generate_request(messages, index, row_fill=False)

        headers = {
            "Authorization": self.token_type + SPACE + self.token,
            "Content-Type": "application/json"
        }

        print("Update headers: ", headers)
        #r = request("POST", url, data=json.dumps(body), headers=headers)
        r = requests.post(url, headers=headers, json=body)
        return r

    def load_gs_prices(self, spreadsheet_id):
        mpn_range = "B1:C"

        url3 = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{mpn_range}"

        # potrzebne?
        headers = {"Authorization": self.token_type + " " + self.token}
        print("Headers load: ", headers)
        r = request("GET", url3, headers=headers)
        data = r.json()
        values = data.get("values", [])
        values=values[1:] #pominiecie nagłowkow

        if "values" not in data:
            print("Brak danych do pobrania z arkusza.")
            return

        global mpn_list, qty_list
        mpn_list = []
        qty_list = []

        for row in values:
            if len(row) >= 1:
                mpn_list.append(row[0])
            if len(row) >= 2:
                qty_list.append(row[1])

        print("MPN-y do przetworzenia:", mpn_list, qty_list)

        #return mpn_list, qty_list

def main():
    # post all important info to Google Sheets
    gs = gsheets(REFRESH_TOKEN_GS)
    #r = gs.update_cells(messages, 3, SID, row_fill=True)

    partnumber = "296-18509-1-ND"

    info=get_product_details(partnumber, token_refreshed)
    price=get_product_unit_price(partnumber, token_refreshed)
    print(price)
    print(info)
    #pninfo=("MPN", "PRICE", "TYPE")
    #infogs=gs.update_cells(pninfo, 0, SID, row_fill=True)

    gs2 = gsheets(REFRESH_TOKEN_GS)
    gs2.load_gs_prices(SID)
    #mpn_list = gs2.load_gs_prices(SID)

    print("QTY LIST:", qty_list)
    print("z globalnej:", mpn_list)

    # 2. Dla każdego MPN pobieramy cenę
    #for i, mpn in enumerate(mpn_list):
    for i, (mpn, qty) in enumerate(zip(mpn_list, qty_list)):
        price = get_product_unit_price(mpn, token_refreshed)
        print(f"{mpn}:{qty}:{price}")
        # Wiersz i + 1 bo dane zaczynają się od A2 (czyli rowIndex = 1)

        gs2.update_cells(
            messages=[price],
            index=8+i,  # rząd w arkuszu
            spreadsheet_id=SID,
            row_fill=True
        )

    #mpn_list = ["SN74LS00N", "NE555P", "LM358N", "ATMEGA328P-PU"]
    #start_row=10
    # for i, mpn in enumerate(mpn_list):
    #     price = get_product_unit_price(mpn, token_refreshed)
    #     row_data = [mpn, price]
    #     gs.update_cells(row_data, start_row, SID, row_fill=True)
    #     start_row=start_row+1

if __name__ == "__main__":
    main()


