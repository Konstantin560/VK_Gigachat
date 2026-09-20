import random

import requests

import config

_session = requests.Session()
logger = __import__("logging").getLogger("vk")


class VkApiError(RuntimeError):
    pass


def _api_call(method, params):
    payload = {
        "access_token": config.VK_GROUP_TOKEN,
        "v": config.VK_API_VERSION,
        **params,
    }
    try:
        resp = _session.post(
            f"{config.VK_API_URL}/{method}",
            data=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise VkApiError(f"Сетевая ошибка VK API ({method}): {exc}") from exc

    data = resp.json()
    if "error" in data:
        err = data["error"]
        raise VkApiError(f"VK API ошибка ({method}): {err.get('error_code')} {err.get('error_msg')}")
    return data.get("response")


def get_long_poll_server():
    response = _api_call(
        "groups.getLongPollServer",
        {"group_id": int(config.VK_GROUP_ID)},
    )
    server, key, ts = response["server"], response["key"], response["ts"]
    logger.info("Long Poll server: %s, ts=%s", server, ts)
    return server, key, ts


def send_message(peer_id, text):
    return _api_call(
        "messages.send",
        {
            "peer_id": peer_id,
            "message": text,
            "random_id": random.randint(1, 2 ** 31),
            "dont_parse_links": 1,
        },
    )


def send_typing(peer_id):
    try:
        _api_call("messages.setActivity", {"peer_id": peer_id, "type": "typing", "group_id": int(config.VK_GROUP_ID)})
    except VkApiError:
        pass


def _long_poll_events(server, key, ts):
    while True:
        base = server if server.startswith(("http://", "https://")) else f"https://{server}"
        url = f"{base}?act=a_check&key={key}&ts={ts}&wait={config.LONG_POLL_WAIT}&mode=2&version=3"
        try:
            resp = _session.get(url, timeout=config.LONG_POLL_WAIT + 10)
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("a_check сетевая ошибка: %s", exc)
            server, key, ts = get_long_poll_server()
            continue

        if data.get("failed"):
            logger.warning("a_check failed: %s", data)
            server, key, ts = get_long_poll_server()
            continue

        ts = data.get("ts", ts)
        updates = data.get("updates", [])
        if updates:
            logger.info("получено обновлений: %d", len(updates))
            yield updates


def long_poll_session():
    server, key, ts = get_long_poll_server()
    return _long_poll_events(server, key, ts)
