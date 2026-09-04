import re
import requests

s = requests.Session()
login = s.post(
    "http://127.0.0.1:5000/login",
    data={"username": "admin", "password": "admin"},
    allow_redirects=False,
    timeout=10,
)
print("login", login.status_code, login.headers.get("Location"))

resp = s.get("http://127.0.0.1:5000/", timeout=30)
ids = set(re.findall(r'id="bt-([^"]+)"', resp.text))
print("index", resp.status_code, "tandas_html", len(ids))
print("sample", sorted(list(ids))[:10])
