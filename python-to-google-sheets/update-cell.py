import requests
from requests import request
import json
import time
import sys
from urllib.parse import quote
import os
from dotenv import load_dotenv

load_dotenv()

# 1.1 Wypelnij Google Cloud credentials
CLIENT_ID_GS = os.getenv("CLIENT_ID_GS")
CLIENT_SECRET_GS = os.getenv("CLIENT_SECRET_GS")
REFRESH_TOKEN_GS = os.getenv("REFRESH_TOKEN_GS")

# 1.2 Wpisz arkusz zakupowy - ID
SID = "1vPCcRckm19n-xNM6MCJcex5ROcxfh-UfaOZ8tie0mXg"

# 1.3 GENEROWANIE KODU DO TOKENU DK
# Wklej link do przeglądarki, wyciagnij zmienną code, odkommentuj wywołanie get_access_code - masz na to 15 sek bo inaczej token przestanie działać
# https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id=QPAeO3l8voXVPZvGGchxcfGq0rTZDuOa&redirect_uri=https://localhost
code = 'ZDKXs4n9'  # CODE TO INITIATE AUTH
token_filename = 'digi_token.json'
test_partnumber = 'BSS138'

SPACE = " "

#INPUT DATA
SHEET_ID = 713868903
SHEET_NAME="baza_linki_oferty"
START_ROW = 2
COL_QTY = "W"
COL_MPN = "E"  #MPN (K) mniej blanków niz DK MPN (J)

# COL_STATUS = 21 #V
# COL_PRICE = 24 #X
COL_STATUS = 24
COL_PRICE = 10

def load_token_from_file(filename):
    with open(filename, 'r') as f:
        token = json.load(f)

    if token != False:
        print('\033[32mToken load SUCCESS.\033[0m')
    else:
        print('\033[31m\033[1mToken load FAILED.\033[0m')
    return token

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

# 1.4 AKTYWACJA TOKENU - funkcja uruchamiana 1 raz na początku do aktywacji tokenu
# Po udanej aktywacji zacommentować!
#get_access_token(code, token_filename)


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

token = load_token_from_file('digi_token.json')

# Token do automatycznego odswiezania API i otrzymywania odpowiedz (response <- requests)
token_refreshed = get_refresh_token(token, token_filename)

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

def get_product_details(partnumber, token):
    partnumber_quoted = partnumber.replace('/', '%2F')
    partnumber_quoted = partnumber_quoted.replace('+', '%2B')
    partnumber_quoted = partnumber_quoted.replace('#', '%23')
    url = f'https://api.digikey.com/Search/v3/Products/{partnumber_quoted}'

    print(url)

    url_header = {
        'x-digikey-locale': 'pl',
        'X-DIGIKEY-Locale-Site': 'PL',
        'X-DIGIKEY-Locale-Currency': 'USD', #lub 'PLN'
        'Authorization': f"{token['token_type']} {token['access_token']}",
        'X-DIGIKEY-Client-Id': token['client_id']
    }

    response = requests.get(url, headers=url_header)

    if response.status_code == 200:
        response_dict = response.json()
        print(f'\033[32mGot information for {partnumber}\033[0m')
        return response_dict
    elif response.status_code == 429:
        print(f'\033[31mRate limit (429) reached at {partnumber}\033[0m')
        return "RATE_LIMIT"
    else:
        print(f'\033[31mFailed to get information for {partnumber}\033[0m')
        print(response.status_code, response.reason)
        return False


def get_product_unit_price(response_dict, partnumber, qty):
    if not response_dict:
        print(f'\033[31m\033[1mFailed to fetch PN price: {partnumber}\033[0m')
        return 0
    try:
        # Pobierz listę progów cenowych
        pricing_tiers = response_dict.get('StandardPricing', [])
        qty = int(qty)
        product_status = response_dict.get("ProductStatus", "Unknown")

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

def get_product_status(response_dict):
    if not response_dict:
        return "Not found"

    try:
        return response_dict.get("ProductStatus", "Unknown")
    except:
        return "Unknown"

class gsheets():

    def __init__(self, refresh_tkn):  # Mozna dodać odwołanie do funkcji spoza klasy
        r = refresh_access_token(refresh_tkn)
        data = r.json()
        self.token = data["access_token"]
        self.token_type = data["token_type"]

    # Generowanie ceny do listy prices dla danego MPN+QTY
    # 2.2 WYBIERZ SHEET_ID (PONOWNIE), KOLUMNE I START ROW DO WGRANIA CENY
    def update_price_column(self, spreadsheet_id, prices):

        # Wpisuje kolejne ceny (lista prices) do kolumny V, w kolejnych wierszach od start_row.

        requests_body = []

        for i, price in enumerate(prices, start=START_ROW):
            # Budujemy pojedynczy update dla komórki kolumna{i}
            requests_body.append({
                "updateCells": {
                    "rows": [{"values": [{"userEnteredValue": {"numberValue": price}}]}],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": SHEET_ID,
                              "rowIndex": i - 1,
                              "columnIndex": COL_PRICE}  # Price col - V
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

    # Generowanie statusu do listy statuses dla danego MPN
    # 2.3 WYBIERZ SHEET_ID (PONOWNIE), KOLUMNE I START ROW DO POBRANIA STATUSU
    def update_status(self, spreadsheet_id, statuses):
        requests_body = []


        for i, status in enumerate(statuses, start=START_ROW):
            # budujemy pojedynczy update dla komórki V{i}
            requests_body.append({
                "updateCells": {
                    "rows": [{"values": [{"userEnteredValue": {"stringValue": status}}]}],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": SHEET_ID,
                              "rowIndex": i - 1,
                              "columnIndex": COL_STATUS}  # Status col - T
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


    def load_gs_prices(self, spreadsheet_id, header_row=1):
        # 2.4 WSKAZAC KTORE KOLUMNY I W JAKIM ARKUSZU CHCEMY POBRAC DO LISTY ILOSCI!
        # 2.5 WSKAZAC KTORE KOLUMNY I W JAKIM ARKUSZU CHCEMY POBRAC DO LISTY CEN!
        # QTY
        range_e = f"{SHEET_NAME}!{COL_QTY}{START_ROW}:{COL_QTY}"
        # MPN
        range_k = f"{SHEET_NAME}!{COL_MPN}{START_ROW}:{COL_MPN}"
        url_template = "https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{rng}"

        headers = {"Authorization": f"{self.token_type} {self.token}"}

        # GET QTY
        r1 = requests.get(url_template.format(sid=spreadsheet_id, rng=range_e),
                          headers=headers)
        qty = [row[0] if row else "" for row in r1.json().get("values", [])]

        # GET MPN
        r2 = requests.get(url_template.format(sid=spreadsheet_id, rng=range_k),
                          headers=headers)
        mpn = [row[0] if row else "" for row in r2.json().get("values", [])]

        # Zwraca 2 listy tej samej długosci
        length = max(len(qty), len(mpn))
        qty += [""] * (length - len(qty))
        mpn += [""] * (length - len(mpn))

        #Debug: qty i mpn
        print("URL QTY:", url_template.format(sid=spreadsheet_id, rng=range_e))
        print("URL PN:", url_template.format(sid=spreadsheet_id, rng=range_k))
        print("Response QTY:", r1.status_code, r1.text)
        print("Response PN:", r2.status_code, r2.text)

        return mpn, qty


def main():

    # Tworzenie nowej klasy - odw. do wiersza 246
    gs2 = gsheets(REFRESH_TOKEN_GS)

    #start test
    partnumber = "296-18509-1-ND"

    info = get_product_details(partnumber, token_refreshed)

    print(info)

    # Pobieranie listy partnumber i quantity z odpowiadających sobie wierszy
    # 2.6 USTAWIC WIERSZ I KOLUMNE STARTOWA
    mpn_list, qty_list = gs2.load_gs_prices(SID, header_row=1)

    print("MPNy:", mpn_list)
    print("Qty:", qty_list)

    prices = []
    statuses = []

    for mpn, qty in zip(mpn_list, qty_list):
        if not mpn.strip():
            statuses.append("Not found")
            prices.append(0)
            continue
            
        qty_int = int(qty) if qty else 1
        
        # Pobieramy detale API tylko RAZ dla danego partnumber
        response_dict = get_product_details(mpn, token_refreshed)
        
        if response_dict == "RATE_LIMIT":
            print("\033[33mOsiągnięto limit zapytań API (429). Przerywam pobieranie i zapisuję dotychczasowe dane.\033[0m")
            break
        
        price = get_product_unit_price(response_dict, mpn, qty_int)
        status = get_product_status(response_dict)
        
        statuses.append(status)
        prices.append(price)
        
        # Krótka pauza żeby nie złapać blokady 429 Too Many Requests
        time.sleep(0.3)


    # Update kolumny price
    response = gs2.update_price_column(SID, prices)
    print("Status update:", response.status_code, response.text)

    # Update kolumny status
    response_status = gs2.update_status(SID, statuses)
    print("Status update:", response_status.status_code, response_status.text)


if __name__ == "__main__":
    main()


