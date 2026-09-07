# python-to-google-sheets

Skrypt czyta MPN i ilości z Google Sheets, dociąga status i cenę z API Digi-Key i zapisuje wyniki z powrotem do arkusza.

Sekrety (`/.env`, `digi_token.json`) są tylko lokalne — w repo są wyłącznie szablony.

## Wymagane pliki lokalne

Skopiuj szablony i uzupełnij wartości (nie commituj kopii):

```text
copy .env.example .env
copy digi_token.example.json digi_token.json
```

### `.env` (Google Sheets)

| Zmienna | Opis |
|---|---|
| `CLIENT_ID_GS` | Client ID z Google Cloud Console |
| `CLIENT_SECRET_GS` | Client secret z Google Cloud Console |
| `REFRESH_TOKEN_GS` | Refresh token OAuth (scope `https://www.googleapis.com/auth/spreadsheets`) |

Jednorazowo: otwórz URL autoryzacji Google (Chrome), wklej `code` do `ACCESS_CODE` w `get-refresh.py` i uruchom skrypt — w odpowiedzi dostaniesz `refresh_token` do `.env`.

### `digi_token.json` (Digi-Key)

| Pole | Opis |
|---|---|
| `client_id` | Client ID aplikacji Digi-Key |
| `client_secret` | Client secret aplikacji Digi-Key |
| `access_token` | Uzupełniane po OAuth / odświeżeniu |
| `refresh_token` | Uzupełniane po OAuth / odświeżeniu |
| `expires_in` | Żywotność access tokenu (sekundy) |
| `refresh_token_expires_in` | Żywotność refresh tokenu (sekundy) |
| `token_type` | Zwykle `Bearer` |
| `refresh_token_time` | Unix timestamp ostatniego odświeżenia |

Na start wystarczą `client_id` i `client_secret`. Resztę zapisze `get_access_token` po jednorazowej autoryzacji Digi-Key (kod z URL `/v1/oauth2/authorize`, potem odkomentowanie wywołania w `update-cell.py`). Kolejne uruchomienia odświeżają token z tego pliku.

## Uruchomienie

```text
pip install requests python-dotenv
python update-cell.py
```

ID arkusza, nazwa zakładki i kolumny są na razie w `update-cell.py` (`SID`, `SHEET_NAME`, `COL_MPN`, `COL_QTY`, …).
