import subprocess
import tempfile
import os
from urllib.parse import urlencode

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

def curl_get(url, cookies, headers, params):
    cmd = ["curl", "-s", "-L", "-G", url]
    for k, v in params.items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    for k, v in cookies.items():
        cmd += ["-b", f"{k}={v}"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd += ["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout

def curl_post(url, cookies, headers, form_data, params):
    if params:
        url = url + "?" + urlencode(params)

    cmd = ["curl", "-s", "-L", "-X", "POST", url]
    for k, v in cookies.items():
        cmd += ["-b", f"{k}={v}"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd += ["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]
    for k, v in form_data.items():
        cmd += ["-d", f"{k}={v}"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout

def curl_upload(url, cookies, headers, files, params):
    if params:
        url = url + "?" + urlencode(params)

    cmd = ["curl", "-s", "-L", "-X", "POST", url]
    for k, v in params.items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    for k, v in cookies.items():
        cmd += ["-b", f"{k}={v}"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd += ["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]

    tmp_files = []
    for filename, content in files:
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix="_" + filename)
        tmp.write(content)
        tmp.close()
        tmp_files.append(tmp.name)
        cmd += ["-F", f"files[]=@{tmp.name};filename={filename}"]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    for tmp in tmp_files:
        os.unlink(tmp)

    return result.stdout

base_url = "http://hw1.alexbers.com/"
user_cookie = { "user": "478a61929cf5fcdea2ea06701e4840d6" }

html = curl_get(base_url, user_cookie, {}, {})

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
        print(html)
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

    all_cookies = {}
    all_cookies.update(user_cookie)
    all_cookies.update(cookies)

    url = base_url + path.lstrip("/")

    if method in ("GET", "LINK"):
        html = curl_get(url, all_cookies, headers, params)
    elif method == "POST":
        html = curl_post(url, all_cookies, headers, form_data, params)
    elif method == "UPLOAD":
        html = curl_upload(url, all_cookies, headers, files_data, params)
    print(f"Все куки: {all_cookies}")