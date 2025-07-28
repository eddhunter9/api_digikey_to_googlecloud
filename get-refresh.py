from requests import request

# 1. Wypelnij credentials - te same co w update_cell
CLIENT_ID = ""
CLIENT_SECRET = ""

# Wklej link do przeglądarki, wybierz konto i wklej code do ACCESS_CODE
# 1-razowo, ale po dłuższym czasie może wymagać ponowienia!
# Uzyj na edge a nie chrome(blokuje dostep)!
# https://accounts.google.com/o/oauth2/auth?access_type=offline&approval_prompt=auto&client_id=1097952590698-er70obviqsgj3jk9psp730lkfta7kqqt.apps.googleusercontent.com&response_type=code&scope=https://www.googleapis.com/auth/spreadsheets&redirect_uri=http://localhost

# 2. Wpisz kod aktywacyjny z url (odpowiedzi) po powyzszym linku
ACCESS_CODE = ""

# 3. Uruchom skrypt, zeby uzyskać refresh token

def main():
    
    url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": ACCESS_CODE,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "redirect_uri": "http://localhost"
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }

    r = request("POST", url, data=data, headers=headers)
    print(r.text)

if __name__ == "__main__":
    main()