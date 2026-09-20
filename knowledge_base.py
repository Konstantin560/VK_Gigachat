import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "knowledge", "zerocoder_knowledge.json")

_general_context = None
_courses = None


def _load():
    global _general_context, _courses
    if _general_context is not None:
        return
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    _general_context = data
    _courses = data["courses"]


def get_general_context():
    _load()
    return _general_context


def _match_keywords(text):
    text = text.lower()
    hits = []
    for course in _courses:
        score = 0
        for kw in course.get("keywords", []):
            if kw.lower() in text:
                score += 1
        if score > 0:
            hits.append((score, course))
    hits.sort(key=lambda item: item[0], reverse=True)
    return [course for _, course in hits]


def build_knowledge_context(user_text=""):
    _load()
    lines = []

    g = _general_context
    lines.append("ОБЩАЯ ИНФОРМАЦИЯ ОБ УНИВЕРСИТЕТЕ:")
    lines.append(f"- Официальное название: {g['general']['full_name']}. Слоган: {g['general']['slogan']}.")
    lines.append(f"- О университете: {g['general']['about']}")
    lines.append(f"- Сообщество и статистика: {g['general']['community']}")
    lines.append(f"- Методы обучения: {g['general']['methods']}")

    lines.append("\nНАПРАВЛЕНИЯ ОБУЧЕНИЯ:")
    for d in g["directions"]:
        lines.append(f"- {d['name']}: {d['description']}")

    matched = _match_keywords(user_text) if user_text else []
    if matched:
        lines.append("\nРЕЛЕВАНТНЫЕ ПРОГРАММЫ (только они подходят к вопросу пользователя):")
        for c in matched:
            lines.append(format_course(c))
        lines.append(
            "\nВажно: точные цены, акции и условия рассрочки не фиксированы и меняются. "
            "Если пользователь спрашивает цену, назовите ориентир, если он есть в базе, "
            "и обязательно предложите связаться с менеджером для точного расчёта."
        )

    lines.append("\nФОРМАТЫ ОБУЧЕНИЯ:")
    f = g["formats"]
    lines.append(f"- Тарифы: {', '.join(f['tariffs'])}.")
    lines.append(f"- {f['tariff_details']['bazoviy']}")
    lines.append(f"- {f['tariff_details']['vip']}")
    lines.append(f"- {f['tariff_details']['vip_plus']}")
    lines.append(f"- Рассрочка: {f['installment']}")
    lines.append(f"- Старт: {f['start']}")

    lines.append("\nКАРЬЕРНЫЙ ЦЕНТР:")
    c = g["career"]
    lines.append(f"- {c['center']}")
    for feat in c["features"]:
        lines.append(f"- {feat}")
    lines.append(f"- Важно: {c['note']}")

    lines.append("\nКОНТАКТЫ И СВЯЗЬ С ОТДЕЛОМ ПРОДАЖ:")
    ct = g["contacts"]
    lines.append(
        f"- Телефон: {ct['phone']}; WhatsApp: {ct['whatsapp']}; "
        f"e-mail: {ct['email']}; сайт: {ct['website']}; поддержка: {ct['support']}"
    )

    lines.append("\nЧАСТЫЕ ВОПРОСЫ:")
    for faq in g["faq"]:
        lines.append(f"- {faq['question']} -> {faq['answer']}")

    return "\n".join(lines)


def format_course(course):
    parts = [f"- Программа «{course['name']}» (категория: {course['category']})"]
    for field in ("duration_months", "duration_hours"):
        if course.get(field):
            unit = "мес." if field == "duration_months" else "ч."
            parts.append(f"  Длительность: {course[field]} {unit}")
    if course.get("format"):
        parts.append(f"  Формат: {course['format']}")
    if course.get("description"):
        parts.append(f"  О чём программа: {course['description']}")
    if course.get("tools"):
        parts.append(f"  Инструменты: {', '.join(course['tools'])}")
    if course.get("price_note"):
        parts.append(f"  Цена: {course['price_note']}")
    return "\n".join(parts)


def list_all_courses():
    _load()
    return "\n".join(format_course(c) for c in _courses)


def get_full_knowledge():
    _load()
    return build_knowledge_context()
