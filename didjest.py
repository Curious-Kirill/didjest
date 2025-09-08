import os
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta

# Загружаем ключи
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

def get_news(query, num=15):
    url = "https://newsapi.org/v2/everything"
    from_date = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    to_date = datetime.utcnow().date().isoformat()
    
    print(f"Поиск новостей за период: {from_date} - {to_date}")
    print(f"Основной запрос: {query}")
    
    # ПОЛНЫЙ СПИСОК ЗАПРОСОВ (АКТИВИРОВАН)
    queries = [
        query,
        "e-grocery Россия",
        "доставка продуктов онлайн Россия",
        "рынок доставки продуктов Россия",
        # Ключевые конкуренты и их комбинации с доставкой/онлайн
        "Самокат доставка",
        "Самокат онлайн",
        "Яндекс Лавка",
        "Яндекс Лавка доставка",
        "Яндекс Лавка программа лояльности",
        "СберМаркет",
        "СберМаркет доставка",
        "Перекресток доставка",
        "Перекрёсток доставка",
        "Пятерочка доставка",
        "Пятёрочка доставка",
        "Магнит доставка",
        "Лента доставка",
        "Окей доставка",
        "Ашан доставка продуктов",
        "Азбука вкуса доставка",
        "Metro доставка продуктов",
        "Ozon доставка продуктов",
        "Wildberries доставка продуктов"
    ]

    

    # КОМБИНИРОВАННЫЙ ЗАПРОС (АКТИВИРОВАН)
    combined_query = (
        '(e-grocery OR "e grocery" OR "быстрая доставка" OR "доставка продуктов") '
        'AND (Самокат OR "Яндекс Лавка" OR Магнит OR СберМаркет OR Перекрёсток OR Пятёрочка OR Лента OR Окей OR Ашан OR Metro OR Ozon OR Wildberries)'
    )
    queries = [combined_query] + queries
    
    print(f"Всего запросов для поиска: {len(queries)}")

    unique_by_url = {}
    for q_idx, q in enumerate(queries):
        if len(unique_by_url) >= num:
            print(f"Достигнут лимит статей ({num}), останавливаю поиск")
            break
            
        print(f"\nЗапрос {q_idx+1}/{len(queries)}: {q[:60]}{'...' if len(q) > 60 else ''}")
        
        for page in range(1, 4):
            params = {
                "apiKey": NEWSAPI_KEY,
                "q": q,
                "language": "ru",
                "sortBy": "publishedAt",
                "searchIn": "title,description,content",
                "pageSize": 100,
                "page": page,
                "from": from_date,
                "to": to_date
            }
            try:
                response = requests.get(url, params=params, timeout=20)
                data = response.json()
                
                if response.status_code != 200:
                    print(f"  Страница {page}: Ошибка API - {response.status_code}: {data.get('message', 'Unknown error')}")
                    continue
                    
                articles = data.get("articles", [])
                print(f"  Страница {page}: найдено {len(articles)} статей")
                
                for item in articles:
                    url_val = item.get("url")
                    if not url_val or url_val in unique_by_url:
                        continue
                    unique_by_url[url_val] = {
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "url": url_val
                    }
                    if len(unique_by_url) >= num:
                        break
                        
                if len(unique_by_url) >= num:
                    break
                    
            except Exception as e:
                print(f"  Страница {page}: Ошибка запроса - {e}")
                continue

    print(f"\nВсего уникальных статей найдено: {len(unique_by_url)}")

    # Фоллбэк: если статей мало, ослабляем фильтры и сортируем по релевантности
    if len(unique_by_url) < max(5, num // 2):
        print(f"\nМало статей ({len(unique_by_url)}), пробую фоллбэк с сортировкой по релевантности...")
        for q_idx, q in enumerate(queries):
            if len(unique_by_url) >= num:
                break
            for page in range(1, 3):
                params = {
                    "apiKey": NEWSAPI_KEY,
                    "q": q,
                    "language": "ru",
                    "sortBy": "relevancy",
                    "searchIn": "title,description,content",
                    "pageSize": 100,
                    "page": page,
                    "from": from_date,
                    "to": to_date
                }
                try:
                    response = requests.get(url, params=params, timeout=20)
                    data = response.json()
                    
                    if response.status_code != 200:
                        continue
                        
                    articles = data.get("articles", [])
                    print(f"  Фоллбэк запрос {q_idx+1}, страница {page}: найдено {len(articles)} статей")
                    
                    for item in articles:
                        url_val = item.get("url")
                        if not url_val or url_val in unique_by_url:
                            continue
                        unique_by_url[url_val] = {
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "url": url_val
                        }
                        if len(unique_by_url) >= num:
                            break
                    if len(unique_by_url) >= num:
                        break
                except Exception:
                    continue

    sources = list(unique_by_url.values())[:num]
    if not sources:
        print("Нет статей для формирования дайджеста")
        return "", {}

    print(f"\nФормирую дайджест из {len(sources)} статей")

    numbered_lines = []
    index_to_url = {}
    for idx, item in enumerate(sources, start=1):
        numbered_lines.append(f"[{idx}] {item['title']} — {item['description']} ({item['url']})")
        index_to_url[idx] = item["url"]
    return "\n".join(numbered_lines), index_to_url

def generate_report(news_text):
    prompt = f"""
Ты — AI-ассистент-ресёрчер. Подготовь обзор по рынку e-grocery в России. Период строго за последние 30 дней.

Вот новости (пронумерованные источники):
{news_text}

Формат:
1. Основные события за последний месяц.
2. Новости ключевых игроков (Самокат, Яндекс Лавка, ВкусВилл, Магнит и др.).
3. Новые технологии и тренды.
4. Риски и возможности для ВкусВилл.

Строгие правила оформления:
- После КАЖДОГО утверждения ставь ссылку-указатель на источник в квадратных скобках вида [n] или [n, m], где n — номер из списка источников выше.
- Используй ТОЛЬКО номера из списка выше. Не выдумывай ссылки и номера.
- Не добавляй ни одного утверждения без номера источника.
- Не ставь лишние знаки по типу *, #, " и т.д.
"""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


def replace_citation_brackets_with_urls(text, index_to_url):
    pattern = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

    def _replace(match):
        numbers = [n.strip() for n in match.group(1).split(',')]
        urls = []
        for n in numbers:
            try:
                idx = int(n)
                url_val = index_to_url.get(idx)
                if url_val:
                    urls.append(url_val)
            except ValueError:
                pass
        return f"({', '.join(urls)})" if urls else match.group(0)

    return pattern.sub(_replace, text)

# Telegram helpers
def _split_for_telegram(text: str, limit: int = 4000):
    if not text:
        return []
    parts = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + limit, n)
        if end < n:
            cut = text.rfind("\n", start, end)
            if cut == -1:
                cut = text.rfind(" ", start, end)
            if cut == -1 or cut <= start:
                cut = end
            parts.append(text[start:cut])
            start = cut
        else:
            parts.append(text[start:end])
            start = end
    return [p for p in (s.strip() for s in parts) if p]

def send_telegram_message(text: str):
    if not TG_TOKEN or not CHAT_ID:
        print("Telegram: пропущено (нет TG_TOKEN или CHAT_ID)")
        return
    api_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    for idx, chunk in enumerate(_split_for_telegram(text), start=1):
        resp = requests.post(
            api_url,
            data={
                "chat_id": CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Telegram error: {resp.status_code} {resp.text}")
        print(f"Telegram: отправлен фрагмент {idx}")

# 3. Запуск
if __name__ == "__main__":
    query = "рынок e-grocery Россия"
    news_text, index_to_url = get_news(query)
    if not news_text:
        print("Нет новостей за выбранный период по заданному запросу.")
    else:
        report = generate_report(news_text)
        report_with_links = replace_citation_brackets_with_urls(report, index_to_url)
        print(report_with_links)
        try:
            send_telegram_message(report_with_links)
            print("Дайджест отправлен в Telegram.")
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")
