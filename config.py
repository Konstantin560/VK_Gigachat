import os

from dotenv import load_dotenv

load_dotenv()


def _env(name, default=""):
    value = os.getenv(name, "")
    if value is None or str(value).strip() == "":
        return default
    return str(value)


VK_GROUP_TOKEN = _env("VK_GROUP_TOKEN")
VK_GROUP_ID = _env("VK_GROUP_ID")
VK_API_VERSION = _env("VK_API_VERSION", "5.199")

GIGACHAT_AUTH_KEY = _env("GIGACHAT_AUTH_KEY")
GIGACHAT_SCOPE = _env("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_MODEL = _env("GIGACHAT_MODEL", "GigaChat-2-Max")
GIGACHAT_VERIFY_SSL = _env("GIGACHAT_VERIFY_SSL", "true").lower() == "true"

VK_API_URL = "https://api.vk.com/method"
GIGACHAT_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_CHAT_URL = "https://api.giga.chat/v1/chat/completions"

MAX_HISTORY_PER_USER = 10
LONG_POLL_WAIT = 25


def validate_env():
    missing = []
    if not VK_GROUP_TOKEN:
        missing.append("VK_GROUP_TOKEN")
    if not VK_GROUP_ID:
        missing.append("VK_GROUP_ID")
    if not GIGACHAT_AUTH_KEY:
        missing.append("GIGACHAT_AUTH_KEY")
    if missing:
        raise RuntimeError(
            "Не заполнены обязательные переменные окружения в файле .env: " + ", ".join(missing)
        )
    if not str(VK_GROUP_ID).strip().lstrip("-").isdigit():
        raise RuntimeError("VK_GROUP_ID должен содержать только число (ID сообщества).")
