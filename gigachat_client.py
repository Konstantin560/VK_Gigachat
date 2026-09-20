import time
import uuid

import requests

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

import config

_session = requests.Session()
_token = None
_token_expires_at = 0

VERIFY = config.GIGACHAT_VERIFY_SSL


class GigaChatError(RuntimeError):
    pass


def _now_ms():
    return int(time.time() * 1000)


def _request_token():
    global _token, _token_expires_at
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": "Basic " + config.GIGACHAT_AUTH_KEY,
    }
    try:
        resp = _session.post(
            config.GIGACHAT_TOKEN_URL,
            headers=headers,
            data={"scope": config.GIGACHAT_SCOPE},
            verify=VERIFY,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise GigaChatError("Не удалось получить токен GigaChat: " + str(exc)) from exc

    if resp.status_code != 200:
        raise GigaChatError(
            f"Ошибка получения токена GigaChat: HTTP {resp.status_code}: {resp.text[:300]}"
        )

    payload = resp.json()
    _token = payload.get("access_token")
    expires_at = payload.get("expires_at", 0)
    if _token is None:
        raise GigaChatError("GigaChat не вернул access_token: " + resp.text[:300])
    _token_expires_at = int(expires_at) - 60_000


def _ensure_token(force=False):
    if force or not _token or _token_expires_at <= _now_ms():
        _request_token()
    return _token


def chat(messages, temperature=0.7, max_tokens=1024):
    token = _ensure_token()
    body = {
        "model": config.GIGACHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
        "User-Agent": "zerocoder-vk-bot",
    }

    for attempt in range(2):
        try:
            resp = _session.post(
                config.GIGACHAT_CHAT_URL,
                headers=headers,
                json=body,
                verify=VERIFY,
                timeout=90,
            )
        except requests.RequestException as exc:
            raise GigaChatError("Не удалось отправить запрос в GigaChat: " + str(exc)) from exc

        if resp.status_code == 401 and attempt == 0:
            token = _ensure_token(force=True)
            headers["Authorization"] = "Bearer " + token
            continue

        if resp.status_code != 200:
            raise GigaChatError(
                f"GigaChat вернул ошибку: HTTP {resp.status_code}: {resp.text[:400]}"
            )

        payload = resp.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GigaChatError("Неожиданный формат ответа GigaChat: " + resp.text[:400]) from exc

        text = content.strip()
        if not text:
            raise GigaChatError("GigaChat вернул пустой ответ.")
        return text

    raise GigaChatError("Не удалось авторизоваться в GigaChat после повторной попытки.")
