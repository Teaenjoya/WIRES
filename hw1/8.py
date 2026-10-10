import requests
import re
from bs4 import BeautifulSoup

def parse_tables(soup):
    cookies = {}
    headers = {}
    form_data = {}
    files = []
    params = {}

    for table in soup.find_all("table"):
        prev = table.find_previous(string=lambda s: s and (
                "cookie" in s.lower()
                or "заголовк" in s.lower()
                or "данные формы" in s.lower()
                or "загрузите файлы" in s.lower()
                or "параметры запроса" in s.lower()
        ))
        prev_text = prev.strip().lower() if prev else ""

        is_cookie = "cookie" in prev_text
        is_headers = "заголовк" in prev_text
        is_form_data = "данные формы" in prev_text
        is_file  = "загрузите файлы" in prev_text
        is_params = "параметры запроса" in prev_text

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)

                if is_cookie:
                    cookies[key] = value
                elif is_headers:
                    headers[key] = value
                elif is_form_data:
                    form_data[key] = value
                elif is_file:
                    files.append((key, value))
                elif is_params:
                    params[key] = value

    return cookies, headers, form_data, files, params

base_url = "http://hw1.alexbers.com/"
user_cookie = { "user": "478a61929cf5fcdea2ea06701e4840d6" }

session = requests.Session()
session.cookies.update(user_cookie)

html = session.get(base_url).text

for step in range(10000):
    soup = BeautifulSoup(html, "html.parser")
    titles = soup.find_all(["h1", "h2"])
    for t in titles:
        print(f"--- {t.get_text(strip=True)} ---")

    cookies, headers, form_data, files_data, params = parse_tables(soup)
    print(f"\n=== Итерация {step + 1} ===")

    print(f"Куки из таблицы: {cookies}")
    print(f"Заголовки из таблицы: {headers}")
    print(f"Данные формы: {form_data}")
    print(f"Параметры запроса: {params}")

    text = soup.get_text()

    if "GET-запрос" in text:
        method = "GET"
    elif "POST-запрос" in text:
        method = "POST"
    elif "Перейдите по ссылке" in text:
        method = "LINK"
    elif "Загрузите файлы" in text:
        method = "UPLOAD"
    else:
        print(text)
        print("конец?")
        break

    if method in ("GET", "POST", "UPLOAD"):
        code = soup.find("code")
        path = code.text.strip()
    else:
        a = soup.find("a", href=True)
        path = a["href"] if a else None
    print(f"Метод: {method}")
    print(f"Путь: {path}")
    session.cookies.clear()
    session.cookies.update(user_cookie)
    session.cookies.update(cookies)

    session.headers.clear()
    session.headers.update(headers)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    url = base_url + path.lstrip("/")

    if method in ("GET", "LINK"):
        response = session.get(url, params=params)
    elif method == "POST":
        response = session.post(url, data=form_data, params=params)
    elif method == "UPLOAD":
        files_data = [
            ("files[]", (filename, content.encode("utf-8"), "application/octet-stream"))
            for filename, content in files_data
        ]
        response = session.post(url, files=files_data, params=params)
        print(html)
    else:
        print(html)
        break

    print(f"Статус: {response.status_code}")
    html = response.text