import json
import logging
import os
import re
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Google OAuth (tylko te trzy z .env) ---
CLIENT_ID_GS = os.getenv("CLIENT_ID_GS")
CLIENT_SECRET_GS = os.getenv("CLIENT_SECRET_GS")
REFRESH_TOKEN_GS = os.getenv("REFRESH_TOKEN_GS")

# --- Arkusz — ustaw ręcznie przed uruchomieniem ---
SID = "1vPCcRckm19n-xNM6MCJcex5ROcxfh-UfaOZ8tie0mXg"
SHEET_ID = 713868903
SHEET_NAME = "baza_linki_oferty"
START_ROW = 886
COL_QTY = "W"
COL_MPN = "E"
COL_PRICE = "K"
COL_STATUS = "Y"

# --- Digi-Key / przebieg ---
TOKEN_FILENAME = "digi_token.json"
DK_LOCALE_SITE = "PL"
DK_LOCALE_LANGUAGE = "pl"
DK_LOCALE_CURRENCY = "USD"
REQUEST_SLEEP_SEC = 0.65
CHECKPOINT_FILE = "checkpoint.json"  # podpowiedź next_row po biegu; start zawsze z START_ROW
LOG_FILE = "run.log"

DK_PRODUCT_DETAILS_URL = "https://api.digikey.com/products/v4/search/{product_number}/productdetails"
DK_KEYWORD_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"
DK_PRICING_BY_QTY_URL = (
    "https://api.digikey.com/products/v4/search/{product_number}/pricingbyquantity/{quantity}"
)
DK_REQUEST_TIMEOUT = 30

JUNK_MPN = {"", "X", "-", "N/A", "NA", "NONE", "NULL", "?", ".", ".."}
AUTH_CODE = ""  # wklej świeży code tylko przy jednorazowej aktywacji OAuth

_details_cache = {}
_price_cache = {}


def setup_logging():
    logger = logging.getLogger("dk_sheets")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


log = setup_logging()


def digikey_authorize_url(filename=TOKEN_FILENAME):
    with open(filename, "r", encoding="utf-8") as f:
        client_id = json.load(f)["client_id"]
    return (
        "https://api.digikey.com/v1/oauth2/authorize"
        f"?response_type=code&client_id={client_id}&redirect_uri=https://localhost"
    )


def load_token_from_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        token = json.load(f)
    if token.get("access_token") or token.get("refresh_token"):
        log.info("Token load SUCCESS")
    else:
        log.warning("Token file loaded, ale brak access/refresh token")
    return token


def get_access_token(auth_code, filename=TOKEN_FILENAME):
    """Jednorazowa wymiana code → tokeny. Nie drukuje secretów."""
    token = load_token_from_file(filename)
    response = requests.post(
        "https://api.digikey.com/v1/oauth2/token",
        data={
            "code": auth_code,
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
            "redirect_uri": "https://localhost",
            "grant_type": "authorization_code",
        },
        timeout=DK_REQUEST_TIMEOUT,
    )
    log.info("get_access_token HTTP %s", response.status_code)
    if response.status_code == 200:
        data = response.json()
        token["access_token"] = data["access_token"]
        token["refresh_token"] = data["refresh_token"]
        token["expires_in"] = data["expires_in"]
        token["refresh_token_expires_in"] = data["refresh_token_expires_in"]
        token["token_type"] = data["token_type"]
        token["refresh_token_time"] = time.time()
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(token, f)
        log.info("Access Token get SUCCESS")
        return token
    log.error("Access Token FAILED: %s", (response.text or "")[:300])
    return False


def get_refresh_token(token, filename=TOKEN_FILENAME):
    if not token:
        return False
    response = requests.post(
        "https://api.digikey.com/v1/oauth2/token",
        data={
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=DK_REQUEST_TIMEOUT,
    )
    if response.status_code == 200:
        data = response.json()
        token["refresh_token_time"] = time.time()
        token["access_token"] = data["access_token"]
        token["refresh_token"] = data["refresh_token"]
        token["expires_in"] = data["expires_in"]
        token["refresh_token_expires_in"] = data["refresh_token_expires_in"]
        token["token_type"] = data["token_type"]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(token, f)
        log.info("Token refresh SUCCESS")
        return token
    log.error("Token refresh FAILED %s %s", response.status_code, response.reason)
    log.warning("Odśwież OAuth Digi-Key (get_access_token) — refresh token nieważny.")
    return token if token.get("access_token") else False


def refresh_google_access_token(refresh_tkn):
    return requests.post(
        "https://accounts.google.com/o/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID_GS,
            "client_secret": CLIENT_SECRET_GS,
            "refresh_token": refresh_tkn,
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=DK_REQUEST_TIMEOUT,
    )


def save_checkpoint(next_row, reason=""):
    """Zapisuje podpowiedź — przy następnym biegu ustaw START_ROW ręcznie w kodzie."""
    payload = {
        "next_row": next_row,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
    }
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(
        "Checkpoint: ustaw START_ROW=%s w update-cell.py przed kolejnym uruchomieniem (%s)",
        next_row,
        reason or "ok",
    )


def parse_qty(qty):
    if qty is None or str(qty).strip() == "":
        return 1
    text = str(qty).strip().replace(" ", "").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return 1
    try:
        value = float(match.group(0))
        return max(1, int(value))
    except ValueError:
        return 1


def is_junk_mpn(mpn):
    cleaned = str(mpn or "").strip().upper()
    if cleaned in JUNK_MPN:
        return True
    if len(cleaned) < 2:
        return True
    return False


def _dk_headers(token):
    return {
        "X-DIGIKEY-Locale-Language": DK_LOCALE_LANGUAGE,
        "X-DIGIKEY-Locale-Site": DK_LOCALE_SITE,
        "X-DIGIKEY-Locale-Currency": DK_LOCALE_CURRENCY,
        "Authorization": f"Bearer {token['access_token']}",
        "X-DIGIKEY-Client-Id": token["client_id"],
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _dk_error_detail(response):
    try:
        data = response.json()
        return data.get("detail") or data.get("ErrorMessage") or data.get("title") or ""
    except Exception:
        return (response.text or "")[:200]


def _retry_after_seconds(response, default=60):
    raw = response.headers.get("Retry-After")
    if not raw:
        return default
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return default


def _unwrap_product(payload, partnumber=None):
    """v4 ProductDetails: {Product}; KeywordSearch / pricing: {Products}."""
    if not payload or not isinstance(payload, dict):
        return None
    product = payload.get("Product")
    if product:
        return product
    products = payload.get("Products") or payload.get("SearchResults") or []
    if isinstance(products, dict):
        products = products.get("Products") or []
    if products:
        needle = str(partnumber or "").strip().upper()
        exact = [
            p for p in products
            if str(p.get("ManufacturerProductNumber", "")).strip().upper() == needle
            or str(p.get("ManufacturerPartNumber", "")).strip().upper() == needle
            or str(p.get("DigiKeyProductNumber", "")).strip().upper() == needle
            or str(p.get("DigiKeyPartNumber", "")).strip().upper() == needle
        ]
        pool = exact or products
        for p in pool:
            if p.get("ProductVariations") or p.get("StandardPricing"):
                return p
        return pool[0]
    if payload.get("StandardPricing") is not None or payload.get("ProductStatus"):
        return payload
    return None


def _price_from_tiers(tiers, qty):
    ordered = sorted(tiers, key=lambda t: t.get("BreakQuantity") or 0)
    best_price = None
    for tier in ordered:
        if qty >= (tier.get("BreakQuantity") or 0):
            best_price = tier.get("UnitPrice")
        else:
            break
    if best_price is not None:
        return best_price
    return ordered[0].get("UnitPrice") if ordered else 0


def _extract_unit_price_from_pricing_payload(payload, qty):
    if not payload:
        return None
    # Częsty kształt PricingByQuantity / ProductPricing
    for key in ("UnitPrice", "QuantityPrice", "Price"):
        if isinstance(payload.get(key), (int, float)):
            return float(payload[key])
    options = payload.get("StandardPricingOptions") or payload.get("PricingOptions") or []
    for option in options:
        products = option.get("Products") or [option]
        for product in products:
            tiers = product.get("StandardPricing") or option.get("StandardPricing") or []
            if tiers:
                return _price_from_tiers(tiers, qty)
            for key in ("UnitPrice", "QuantityPrice", "Price"):
                if isinstance(product.get(key), (int, float)):
                    return float(product[key])
    product = _unwrap_product(payload)
    if product:
        if isinstance(product.get("UnitPrice"), (int, float)):
            return float(product["UnitPrice"])
        tiers = product.get("StandardPricing") or []
        if tiers:
            return _price_from_tiers(tiers, qty)
    return None


def get_pricing_by_quantity(partnumber, qty, token):
    cache_key = (partnumber.strip().upper(), qty)
    if cache_key in _price_cache:
        return _price_cache[cache_key]

    quoted = quote(partnumber, safe="")
    url = DK_PRICING_BY_QTY_URL.format(product_number=quoted, quantity=qty)
    response = requests.get(url, headers=_dk_headers(token), timeout=DK_REQUEST_TIMEOUT)
    log.info("row-pricing | %s qty=%s | PricingByQuantity HTTP %s", partnumber, qty, response.status_code)

    if response.status_code == 429:
        return "RATE_LIMIT", response
    if response.status_code == 200:
        price = _extract_unit_price_from_pricing_payload(response.json(), qty)
        if price is not None:
            _price_cache[cache_key] = price
            return price, response
    return None, response


def _keyword_search_v4(token, partnumber):
    response = requests.post(
        DK_KEYWORD_SEARCH_URL,
        headers=_dk_headers(token),
        json={"Keywords": partnumber, "Limit": 10, "Offset": 0},
        timeout=DK_REQUEST_TIMEOUT,
    )
    log.info("%s | KeywordSearch HTTP %s", partnumber, response.status_code)
    if response.status_code == 429:
        return "RATE_LIMIT"
    if response.status_code == 200:
        data = response.json()
        if _unwrap_product(data, partnumber):
            log.info("%s | source=keyword", partnumber)
            return data
    detail = _dk_error_detail(response)
    if detail:
        log.warning("%s | KeywordSearch detail: %s", partnumber, detail)
    return False


def get_product_details(partnumber, token):
    if not token:
        log.error("Brak tokenu Digi-Key — odśwież OAuth (get_access_token).")
        return False

    partnumber = str(partnumber).strip()
    cache_key = partnumber.upper()
    if cache_key in _details_cache:
        log.info("%s | source=cache", partnumber)
        return _details_cache[cache_key]

    quoted = quote(partnumber, safe="")
    url = DK_PRODUCT_DETAILS_URL.format(product_number=quoted)
    response = requests.get(url, headers=_dk_headers(token), timeout=DK_REQUEST_TIMEOUT)
    log.info("%s | ProductDetails HTTP %s", partnumber, response.status_code)

    if response.status_code == 200:
        data = response.json()
        _details_cache[cache_key] = data
        log.info("%s | source=productdetails", partnumber)
        return data
    if response.status_code == 429:
        wait_s = _retry_after_seconds(response)
        log.warning("%s | RATE_LIMIT (429), Retry-After=%ss", partnumber, wait_s)
        return "RATE_LIMIT"
    if response.status_code == 401:
        log.error("Product Information v4: 401. Włącz v4 i wygeneruj nowy token OAuth.")
        detail = _dk_error_detail(response)
        if detail:
            log.error(detail)
        return False

    # Śmieciowe MPN — nie marnuj KeywordSearch (drugi request)
    if is_junk_mpn(partnumber):
        log.warning("%s | pomijam KeywordSearch (placeholder/junk)", partnumber)
        return False

    log.info("%s | ProductDetails %s → KeywordSearch", partnumber, response.status_code)
    result = _keyword_search_v4(token, partnumber)
    if isinstance(result, dict):
        _details_cache[cache_key] = result
    return result


def get_product_unit_price(response_dict, partnumber, qty, token=None):
    if not response_dict or response_dict == "RATE_LIMIT":
        log.warning("Brak ceny dla %s", partnumber)
        return 0, None

    qty = parse_qty(qty)
    cache_key = (str(partnumber).strip().upper(), qty)
    if cache_key in _price_cache:
        return _price_cache[cache_key], None

    # 1) Najpierw progi z już pobranego ProductDetails / Keyword (bez dodatkowego requestu)
    try:
        product = _unwrap_product(response_dict, partnumber)
        if product:
            variations = product.get("ProductVariations") or []
            candidates = [v for v in variations if v.get("StandardPricing")]
            if not candidates and product.get("StandardPricing"):
                candidates = [product]
            if candidates:
                scored = []
                for variation in candidates:
                    tiers = variation.get("StandardPricing") or []
                    moq = variation.get("MinimumOrderQuantity") or 0
                    stock = (
                        variation.get("QuantityAvailableforPackageType")
                        or variation.get("QuantityAvailable")
                        or 0
                    )
                    price = _price_from_tiers(tiers, qty)
                    scored.append((1 if qty >= moq else 0, 1 if stock else 0, price))
                scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
                price = scored[0][2]
                if isinstance(price, (int, float)) and price > 0:
                    _price_cache[cache_key] = price
                    log.info("%s | price source=variations", partnumber)
                    return price, None
            if isinstance(product.get("UnitPrice"), (int, float)) and product["UnitPrice"] > 0:
                price = float(product["UnitPrice"])
                _price_cache[cache_key] = price
                log.info("%s | price source=unitprice", partnumber)
                return price, None
    except Exception as e:
        log.error("Błąd ceny (variations) dla %s: %s", partnumber, e)

    # 2) PricingByQuantity tylko gdy lokalnie nie ma sensownej ceny
    if token:
        priced, raw = get_pricing_by_quantity(partnumber, qty, token)
        if priced == "RATE_LIMIT":
            return "RATE_LIMIT", raw
        if isinstance(priced, (int, float)):
            log.info("%s | price source=pricingbyquantity", partnumber)
            return priced, None

    log.warning("Brak ceny dla %s", partnumber)
    return 0, None


def get_product_status(response_dict):
    if not response_dict or response_dict == "RATE_LIMIT":
        return "Not found"
    product = _unwrap_product(response_dict)
    if not product:
        return "Not found"
    status = product.get("ProductStatus")
    if isinstance(status, dict):
        return status.get("Status") or "Unknown"
    if status:
        return str(status)
    return "Unknown"


class GSheets:
    def __init__(self, refresh_tkn):
        r = refresh_google_access_token(refresh_tkn)
        data = r.json()
        if "access_token" not in data:
            raise RuntimeError(f"Google OAuth failed: {data}")
        self.token = data["access_token"]
        self.token_type = data.get("token_type", "Bearer")

    def _headers(self):
        return {
            "Authorization": f"{self.token_type} {self.token}",
            "Content-Type": "application/json",
        }

    def load_mpn_qty(self, spreadsheet_id, start_row):
        ranges = [
            f"{SHEET_NAME}!{COL_QTY}{start_row}:{COL_QTY}",
            f"{SHEET_NAME}!{COL_MPN}{start_row}:{COL_MPN}",
        ]
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet"
        response = requests.get(
            url,
            headers=self._headers(),
            params=[("ranges", r) for r in ranges],
            timeout=DK_REQUEST_TIMEOUT,
        )
        log.info("Sheets batchGet HTTP %s", response.status_code)
        if response.status_code != 200:
            raise RuntimeError(f"Sheets read failed: {response.status_code} {response.text[:300]}")

        value_ranges = response.json().get("valueRanges", [])
        qty_values = value_ranges[0].get("values", []) if len(value_ranges) > 0 else []
        mpn_values = value_ranges[1].get("values", []) if len(value_ranges) > 1 else []
        qty = [row[0] if row else "" for row in qty_values]
        mpn = [row[0] if row else "" for row in mpn_values]
        length = max(len(qty), len(mpn))
        qty += [""] * (length - len(qty))
        mpn += [""] * (length - len(mpn))
        return mpn, qty

    def update_price_and_status(self, spreadsheet_id, start_row, prices, statuses):
        if not prices:
            log.info("Brak wierszy do zapisu w Sheets")
            return None
        end_row = start_row + len(prices) - 1
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"{SHEET_NAME}!{COL_PRICE}{start_row}:{COL_PRICE}{end_row}",
                    "values": [[p] for p in prices],
                },
                {
                    "range": f"{SHEET_NAME}!{COL_STATUS}{start_row}:{COL_STATUS}{end_row}",
                    "values": [[s] for s in statuses],
                },
            ],
        }
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
        response = requests.post(url, headers=self._headers(), json=body, timeout=DK_REQUEST_TIMEOUT)
        log.info(
            "Sheets batchUpdate HTTP %s | rows %s-%s | cells=%s",
            response.status_code,
            start_row,
            end_row,
            response.json().get("totalUpdatedCells") if response.status_code == 200 else response.text[:200],
        )
        return response


def main():
    # Jednorazowa aktywacja Digi-Key (odkomentuj / ustaw AUTH_CODE):
    # print("Link do code Digi-Key:", digikey_authorize_url())
    # get_access_token(AUTH_CODE)

    if not all([CLIENT_ID_GS, CLIENT_SECRET_GS, REFRESH_TOKEN_GS]):
        raise SystemExit("Brak CLIENT_ID_GS / CLIENT_SECRET_GS / REFRESH_TOKEN_GS w .env")

    token = load_token_from_file(TOKEN_FILENAME)
    token = get_refresh_token(token, TOKEN_FILENAME)
    if not token:
        raise SystemExit("Brak ważnego tokenu Digi-Key")

    log.info(
        "Start | sheet=%s gid=%s from_row=%s cols MPN=%s QTY=%s PRICE=%s STATUS=%s",
        SHEET_NAME,
        SHEET_ID,
        START_ROW,
        COL_MPN,
        COL_QTY,
        COL_PRICE,
        COL_STATUS,
    )

    gs = GSheets(REFRESH_TOKEN_GS)
    mpn_list, qty_list = gs.load_mpn_qty(SID, START_ROW)
    log.info("Wczytano %s wierszy MPN/QTY od wiersza %s", len(mpn_list), START_ROW)

    prices = []
    statuses = []
    stopped_on_limit = False
    next_row = START_ROW

    for offset, (mpn, qty) in enumerate(zip(mpn_list, qty_list)):
        row_num = START_ROW + offset
        next_row = row_num

        if not str(mpn).strip() or is_junk_mpn(mpn):
            statuses.append("Not found")
            prices.append(0)
            log.info("row=%s | mpn=%r | skipped junk/empty", row_num, mpn)
            next_row = row_num + 1
            continue

        qty_int = parse_qty(qty)
        response_dict = get_product_details(mpn, token)

        if response_dict == "RATE_LIMIT":
            log.warning(
                "429 — przerywam. Zapisuję dotychczasowe dane. Ustaw START_ROW=%s w kodzie.",
                row_num,
            )
            stopped_on_limit = True
            next_row = row_num
            break

        price, rate_raw = get_product_unit_price(response_dict, mpn, qty_int, token=token)
        if price == "RATE_LIMIT":
            log.warning("429 na PricingByQuantity — przerywam na wierszu %s", row_num)
            stopped_on_limit = True
            next_row = row_num
            break

        status = get_product_status(response_dict)
        prices.append(price if isinstance(price, (int, float)) else 0)
        statuses.append(status)
        log.info(
            "row=%s | mpn=%s | qty=%s | price=%s | status=%s",
            row_num,
            mpn,
            qty_int,
            prices[-1],
            status,
        )
        next_row = row_num + 1
        time.sleep(REQUEST_SLEEP_SEC)

    write_resp = gs.update_price_and_status(SID, START_ROW, prices, statuses)
    if write_resp is not None and write_resp.status_code != 200:
        log.error("Zapis do Sheets nieudany — checkpoint zostaje na START_ROW=%s", START_ROW)
        save_checkpoint(START_ROW, reason="sheets_write_failed")
        raise SystemExit(1)

    reason = "rate_limit" if stopped_on_limit else "completed"
    save_checkpoint(next_row, reason=reason)
    log.info(
        "Koniec | zapisano %s wierszy | ustaw START_ROW=%s przed następnym biegiem | reason=%s",
        len(prices),
        next_row,
        reason,
    )


if __name__ == "__main__":
    main()
