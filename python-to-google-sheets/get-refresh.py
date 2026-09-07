from requests import request
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Wypelnij credentials - pobierane z .env (te same co w update_cell)
CLIENT_ID = os.getenv("CLIENT_ID_GS")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_GS")

# Wklej link do przeglądarki, wybierz konto i wklej code do ACCESS_CODE
# 1-razowo, ale po dłuższym czasie może wymagać ponowienia!
# Nie na mozilli! Na chrome
#https://accounts.google.com/o/oauth2/auth?access_type=offline&approval_prompt=auto&client_id=1097952590698-er70obviqsgj3jk9psp730lkfta7kqqt.apps.googleusercontent.com&response_type=code&scope=https://www.googleapis.com/auth/spreadsheets&redirect_uri=http://localhost

ACCESS_CODE = "4/0AVMBsJg3Q8xDfKYnJL-bbCAeSNp6yEI0ixHWzw3s74KyGGd4cjbcSrzkJflJwl0vWZowDQ"

# 2. Uruchom skrypt, zeby uzyskać refresh token

def main():
    # get refresh token/access token from access code
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