import requests
from requests import request
import json
import time
import sys
from urllib.parse import quote

#Google Cloud credentials
CLIENT_ID_GS = "1097952590698-er70obviqsgj3jk9psp730lkfta7kqqt.apps.googleusercontent.com"
CLIENT_SECRET_GS = "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"
REFRESH_TOKEN_GS = "1//0310H4-wlMA7MCgYIARAAGAMSNwF-L9Ir2mM15p-bJdZ5Gq46XL5bTpq6uvDZ-lOWw5e94tdKYUwPgC1pY_zed_zIJJelMt8Nja4"

#Arkusz zakupowy
SID = "1vPCcRckm19n-xNM6MCJcex5ROcxfh-UfaOZ8tie0mXg"

#Zmienna code wyciągnięta po odpowiedzi z przeglądarki
# https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id=QPAeO3l8voXVPZvGGchxcfGq0rTZDuOa&redirect_uri=https://localhost
code = 'YVUXJ4YA'  # CODE TO INITIATE AUTH
token_filename = 'digi_token.json'
test_partnumber = 'BSS138'

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

#Funkcja uruchamiana 1 raz na początku do aktywacji tokenu
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
                "sheetId": 1233158800,
                "rowIndex": row,
                "columnIndex": col
            }
        }
    }
    return cell


def generate_request(messages, index, row_fill):
    #requests.append(a_cell(messages,4,4))

    #Zabezpieczenie zeby przesyłała sie cena jako pojedynczy arg
    if not isinstance(messages, (list, tuple)):
        messages = [messages]

    requests = []

    if row_fill:
        for i in range(len(messages)):
            requests.append(a_cell(messages[i], index, i))
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
    #url2 = f'"https://www.digikey.com/en/products/result?keywords={partnumber_quoted}'
    print(url)

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


# def get_product_unit_price(partnumber, token):
#     response_dict = get_product_details(partnumber, token)
#     if response_dict == False:
#         print(f'\033[31m\033[1mFailed to fetch PN price: {partnumber}\033[0m')
#         return 0
#     else:
#         try:
#             price = response_dict['StandardPricing'][0]['UnitPrice']
#             return price
#         except:
#             return 0

def get_product_unit_price(partnumber, token, qty):
    response_dict = get_product_details(partnumber, token)
    if not response_dict:
        print(f'\033[31m\033[1mFailed to fetch PN price: {partnumber}\033[0m')
        return 0
    try:
        # Pobierz listę progów cenowych
        pricing_tiers = response_dict.get('StandardPricing', [])
        qty = int(qty)
        product_status=response_dict.get("ProductStatus", "Unknown")

        # Znajdź najbliższy próg nie większy niż qty
        best_price = None
        for tier in pricing_tiers:
            if qty >= tier['BreakQuantity']:
                best_price = tier['UnitPrice']
            else:
                break

        if best_price is not None:
            return best_price
        else:
            return pricing_tiers[0]['UnitPrice'] if pricing_tiers else 0
    except Exception as e:
        print(f'Błąd przy przetwarzaniu ceny dla {partnumber}: {e}')
        return 0

def get_product_status(partnumber, token):
    response_dict = get_product_details(partnumber, token)
    if not response_dict:
        return "Not found"

    try:
        return response_dict.get("ProductStatus", "Unknown")
    except:
        return "Unknown"


class gsheets():

    def __init__(self, refresh_tkn):  #mozna dodać odwołanie do funkcji spoza klasy
        r = refresh_access_token(refresh_tkn)
        data = r.json()
        self.token = data["access_token"]
        self.token_type = data["token_type"]

    def update_price_column(self, spreadsheet_id, prices, start_row=5):
        """
        Wpisuje kolejne ceny (lista prices) do kolumny V, w kolejnych wierszach od start_row.
        """
        requests_body = []

        for i, price in enumerate(prices, start=start_row):
            # budujemy pojedynczy update dla komórki V{i}
            requests_body.append({
                "updateCells": {
                    "rows": [{"values": [{"userEnteredValue": {"numberValue": price}}]}],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": 1233158800,
                              "rowIndex": i - 1,
                              "columnIndex": 21}  # price col - V
                }
            })

        body = {"requests": requests_body}
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        headers = {
            "Authorization": f"{self.token_type} {self.token}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, headers=headers, json=body)
        return r

    def update_status(self, spreadsheet_id, statuses, start_row=5):
        requests_body = []

        for i, status in enumerate(statuses, start=start_row):
            # budujemy pojedynczy update dla komórki V{i}
            requests_body.append({
                "updateCells": {
                    "rows": [{"values": [{"userEnteredValue": {"stringValue": status}}]}],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": 1233158800,
                              "rowIndex": i - 1,
                              "columnIndex": 19}  # status col - U
                }
            })

        body = {"requests": requests_body}
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        headers = {
            "Authorization": f"{self.token_type} {self.token}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, headers=headers, json=body)
        return r


    def load_gs_prices(self, spreadsheet_id, header_row=1, start_row=5):
        # Pobieramy E2:E i J2:J
        #QTY
        range_e = f"DO-254_THALES_FMC_FCM_HES-M2GL025-FGG484IDB!E{start_row}:E"
        #DPN
        range_k = f"DO-254_THALES_FMC_FCM_HES-M2GL025-FGG484IDB!K{start_row}:J"
        url_template = "https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{rng}"

        headers = {"Authorization": f"{self.token_type} {self.token}"}

        # GET ilości
        r1 = requests.get(url_template.format(sid=spreadsheet_id, rng=range_e),
                          headers=headers)
        qty = [row[0] if row else "" for row in r1.json().get("values", [])]

        # GET MPN
        r2 = requests.get(url_template.format(sid=spreadsheet_id, rng=range_k),
                          headers=headers)
        mpn = [row[0] if row else "" for row in r2.json().get("values", [])]

        # zwróć dwie listy tej samej długości
        length = max(len(qty), len(mpn))
        qty += [""] * (length - len(qty))
        mpn += [""] * (length - len(mpn))

        #debug printy
        print("URL QTY:", url_template.format(sid=spreadsheet_id, rng=range_e))
        print("URL PN:", url_template.format(sid=spreadsheet_id, rng=range_k))
        print("Response QTY:", r1.status_code, r1.text)
        print("Response PN:", r2.status_code, r2.text)

        return mpn, qty


def main():
    # post all important info to Google Sheets
    gs = gsheets(REFRESH_TOKEN_GS)

    gs2 = gsheets(REFRESH_TOKEN_GS)

    partnumber = "296-18509-1-ND"

    info = get_product_details(partnumber, token_refreshed)
    #price = get_product_unit_price(partnumber, token_refreshed)
    #print(price)
    print(info)

    #Pobieranie listy partnumber i quantity z odpowiadających sobie wierszy
    mpn_list, qty_list = gs2.load_gs_prices(SID, header_row=1, start_row=5)
    #mpn_list, qty_list = gs2.load_gs_prices(SID)
    print("MPNy:", mpn_list)
    print("Qty:", qty_list)


    prices = []
    statuses = []

    for mpn, qty in zip(mpn_list, qty_list):
        qty_int = int(qty) if qty else 1
        price = get_product_unit_price(mpn, token_refreshed, qty_int)  # Twoja funkcja z progiem
        status = get_product_status(mpn, token_refreshed)
        prices.append(price)
        statuses.append(status)

    #Update kolumny price
    response = gs2.update_price_column(SID, prices)
    print("Status update:", response.status_code, response.text)

    #Update kolummny status
    response_status = gs2.update_status(SID, statuses)
    print("Status update:", response_status.status_code, response_status.text)

    # for i, (mpn, qty) in enumerate(zip(mpn_list, qty_list)):
    #     qty = qty_list[i] if i < len(qty_list) else 1  # domyślnie 1 jeśli brak
    #     price = get_product_unit_price(mpn, token_refreshed, qty)
    #     print(f"{mpn}:{qty}:{price}")
    #     # Wiersz i + 1 bo dane zaczynają się od A2 (czyli rowIndex = 1)
    #
    #     gs2.update_cells(
    #         messages=[price],
    #         index=i+1,  # rząd w arkuszu
    #         spreadsheet_id=SID,
    #         row_fill=True
    #     )

if __name__ == "__main__":
    main()


