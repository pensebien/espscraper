import requests
r = requests.get("https://espweb.asicentral.com/")
print(r.status_code, r.text)