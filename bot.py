import logging
import os
import sys
import time

import config
import gigachat_client
import vk_client
from knowledge_base import build_knowledge_context, get_general_context
from system_prompt import SYSTEM_PROMPT

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import fcntl
except ImportError:
    fcntl = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("bot")

VK_MAX_MESSAGE_LEN = 4096
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.lock")

history = {}


class SingleInstance:
    def __init__(self, path):
        self.path = path
        self.fh = None
        self.is_locked = False

    def acquire(self):
        self.fh = open(self.path, "a+")
        self.fh.seek(0)
        try:
            if msvcrt is not None:
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            elif fcntl is not None:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise RuntimeError("Не поддерживаемая платформа")
            self.is_locked = True
            self.fh.seek(0)
            self.fh.truncate()
            self.fh.write(str(os.getpid()))
            self.fh.flush()
        except OSError:
            self._cleanup()
        return self.is_locked

    def _cleanup(self):
        try:
            self.fh.close()
        except OSError:
            pass
        self.fh = None
        self.is_locked = False

    def release(self):
        if self.fh is not None:
            try:
                if msvcrt is not None:
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
                elif fcntl is not None:
                    fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.fh.close()
            self.fh = None
        try:
            os.remove(self.path)
        except OSError:
            pass


def build_system_content(user_text):
    knowledge = build_knowledge_context(user_text)
    return SYSTEM_PROMPT + "\n\n# БАЗА ЗНАНИЙ ОБ УНИВЕРСИТЕТЕ ZEROCODER\n" + knowledge


def split_message(text):
    text = text.strip()
    if len(text) <= VK_MAX_MESSAGE_LEN:
        return [text]
    chunks = []
    while len(text) > VK_MAX_MESSAGE_LEN:
        cut = text.rfind("\n", 0, VK_MAX_MESSAGE_LEN)
        if cut <= 0:
            cut = text.rfind(". ", 0, VK_MAX_MESSAGE_LEN)
        if cut <= 0:
            cut = VK_MAX_MESSAGE_LEN
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks


def get_user_history(peer_id):
    return history.setdefault(peer_id, [])


def append_to_history(peer_id, role, content):
    messages = get_user_history(peer_id)
    messages.append({"role": role, "content": content})
    del messages[:-config.MAX_HISTORY_PER_USER]


def handle_message(peer_id, text):
    logger.info("Сообщение от peer_id=%s: %s", peer_id, text[:200])
    vk_client.send_typing(peer_id)

    system_content = build_system_content(text)
    user_history = get_user_history(peer_id)
    payload_messages = [
        {"role": "system", "content": system_content},
        *user_history,
        {"role": "user", "content": text},
    ]

    try:
        reply = gigachat_client.chat(payload_messages, temperature=0.7, max_tokens=1024)
    except gigachat_client.GigaChatError as exc:
        logger.error("Ошибка GigaChat: %s", exc)
        contacts = get_general_context()["contacts"]
        reply = (
            "Ой, у меня что-то случилось с голосом 😅 Попробуй написать ещё раз. "
            f"Если вопрос срочный, менеджер Zerocoder ответит быстрее: {contacts['phone']}."
        )

    append_to_history(peer_id, "user", text)
    append_to_history(peer_id, "assistant", reply)

    for chunk in split_message(reply):
        vk_client.send_message(peer_id, chunk)
        time.sleep(0.3)


def main():
    single = SingleInstance(LOCK_FILE)
    if not single.acquire():
        logger.error("Бот уже запущен. Завершаю работу, чтобы не было дублей ответов (lock: %s).", LOCK_FILE)
        sys.exit(1)

    try:
        _run()
    finally:
        single.release()


def _run():
    config.validate_env()
    logger.info("Бот Алина из Zerocoder запущен (сообщество ВК, модель GigaChat=%s)", config.GIGACHAT_MODEL)

    try:
        long_poll = vk_client.long_poll_session()
    except vk_client.VkApiError as exc:
        logger.error(
            "Не удалось подключиться к Long Poll ВКонтакте. Проверьте VK_GROUP_TOKEN, VK_GROUP_ID "
            "и права бота (messages). Ошибка: %s",
            exc,
        )
        sys.exit(1)

    for updates in long_poll:
        for event in updates:
            try:
                if event.get("type") != "message_new":
                    continue
                message = event.get("object", {}).get("message", {})
                text = (message.get("text") or "").strip()
                peer_id = message.get("peer_id")
                if not text or peer_id is None:
                    continue
                handle_message(peer_id, text)
            except vk_client.VkApiError as exc:
                logger.error("Ошибка VK API: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Непредвиденная ошибка при обработке события: %s", exc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
        sys.exit(0)
