# python-to-google-sheets

Skrypt czyta MPN i ilości z Google Sheets, dociąga status i cenę z Digi-Key Product Information **v4** i zapisuje wyniki do arkusza.

Sekrety (`.env`, `digi_token.json`) są tylko lokalne — w repo są szablony.

## Setup

```text
copy .env.example .env
copy digi_token.example.json digi_token.json
pip install -r requirements.txt
```

### `.env` (tylko Google OAuth)

| Zmienna | Opis |
|---|---|
| `CLIENT_ID_GS` | Client ID z Google Cloud Console |
| `CLIENT_SECRET_GS` | Client secret |
| `REFRESH_TOKEN_GS` | Refresh token (scope `spreadsheets`) |

Jednorazowo: `get-refresh.py` (Chrome) → `refresh_token` do `.env`.

### `digi_token.json` (Digi-Key)

Jak w `digi_token.example.json`. Aplikacja musi mieć **Product Information V4**.

Jednorazowy OAuth Digi-Key: link z `digikey_authorize_url()`, potem `get_access_token("CODE")` w `update-cell.py`.

## Konfiguracja przed każdym biegiem

W `update-cell.py` ustaw ręcznie i sprawdź:

- `START_ROW` — od którego wiersza czytać/pisać
- `SID`, `SHEET_ID`, `SHEET_NAME`
- `COL_MPN`, `COL_QTY`, `COL_PRICE`, `COL_STATUS`

Po 429 / końcu biegu skrypt zapisuje podpowiedź `next_row` do `checkpoint.json` i logu — **nie startuje z niej automatycznie**; wklejasz wartość do `START_ROW` sam.

## Uruchomienie

```text
python update-cell.py
```

Skrypt dodatkowo: loguje do `run.log`, cache’uje MPN, pomija placeholdery (`X`, `N/A`, …), bierze cenę z progów / ewentualnie PricingByQuantity, przy 429 przerywa i zapisuje zebrane wiersze.
