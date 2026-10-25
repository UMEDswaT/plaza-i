"""AI and Meta WhatsApp communication."""
import re
import httpx
from app.prompt import SYSTEM_PROMPT, PRICE_REPLY_TG, PRICE_REPLY_RU

# Some messages are handled deterministically before involving an LLM.
PRICE_QUERY = re.compile(r"(?:нарх|нархаш|чанд\s*(?:сомон|пул)|маблағ|арзиш|расценк|сколько\s+стоит|сколько\s+будет|стоимост|цен[ауые]|прайс)", re.I)
HUMAN_QUERY = re.compile(r"(?:менеҷер|менеджер|бо\s+одам|с\s+человеком|живой\s+оператор|сотрудник|оператор|позвонит|занг\s+зан|мастер\s+позвон)", re.I)
PRICE_OUTPUT = re.compile(r"(?:\d[\d\s,.]*\s*(?:сомон\w*|tjs|usd|доллар\w*|руб\w*|\$|€)|(?:нарх|стоимост\w*|цена)\s*(?:аз|от)?\s*\d)", re.I)
TG_MARKERS = re.compile(
    r"[ӣӯқҷғҳ]|\\b(?:салом|ассалому|ман|хона|мехоҳам|мехохам|мехом|мешавад|метонед|метавонед|чанд|"
    r"даркор|лоиҳа|куҷо|кучо|суроға|сурога|мехостам|мехохем|ташаккур|нарх|бигӯед|мегуед)\\b", re.I)
TG_LATIN_MARKERS = re.compile(
    r"\\b(?:salom|assalomu|man|mehoham|mekhoham|mekhom|loiha|khona|chand|darkor|kujo|suroga)\\b", re.I)
RU_MARKERS = re.compile(
    r"\\b(?:привет|здравствуйте|нужен|нужна|хочу|сколько|где|можно|спасибо|"
    r"квартира|квартиры|квартиру|стоимость|менеджер|адрес|проект|подскажите|"
    r"сделать|нужно|интересует|пожалуйста)\\b", re.I)


def is_tajik(message: str, conversation=()) -> bool:
    """Detect the current language, preserving context for short ambiguous replies."""
    if TG_MARKERS.search(message) or TG_LATIN_MARKERS.search(message):
        return True
    if RU_MARKERS.search(message):
        return False
    # The transcript may already contain the current user message.
    for item in reversed(list(conversation)):
        if item.get('role') != 'user':
            continue
        previous = item.get('body', '')
        if previous == message:
            continue
        if TG_MARKERS.search(previous) or TG_LATIN_MARKERS.search(previous):
            return True
        if RU_MARKERS.search(previous):
            return False
    return not bool(re.search(r"[а-яё]", message, re.I))


def needs_handoff(message: str) -> bool:
    return bool(PRICE_QUERY.search(message) or HUMAN_QUERY.search(message))


def handoff_message(message: str, history=()) -> str:
    tajik = is_tajik(message, history)
    if PRICE_QUERY.search(message):
        return (PRICE_REPLY_TG if tajik else PRICE_REPLY_RU) + (" Суҳбат барои идомаи менеҷер қайд шуд." if tajik else " Обращение отмечено для менеджера.")
    return ("Суҳбат барои идомаи кор бо менеҷери PLAZA-I қайд шуд." if tajik else "Обращение отмечено для продолжения разговора с менеджером PLAZA-I.")


def demo_reply(text: str, history=()) -> str:
    """Offline visual simulation ONLY; no AI/network requests."""
    tajik = is_tajik(text, history)
    low = text.lower()
    if any(s in low for s in ('суроға','адрес','куҷо','где находит')):
        return ('Суроғаи PLAZA-I: Душанбе, кӯчаи Соҳили 22, назди кӯдакистони «Закия».' if tajik else 'Адрес PLAZA-I: Душанбе, ул. Сохили, 22, рядом с детским садом «Закия».')
    if any(s in low for s in ('дизайн','дизайнер','интерьер')):
        return ('Албатта, ширкати PLAZA-I дизайни дохилиро анҷом медиҳад. Масоҳати хонаатон чанд метри мураббаъ аст?' if tajik else 'Конечно, PLAZA-I выполняет дизайн интерьера. Какова примерная площадь помещения?')
    if any(s in low for s in ('лоиҳа','архитект','проект','меъмор')):
        return ('PLAZA-I ба лоиҳакашии меъморӣ машғул аст. Лоиҳа барои хонаи шахсӣ аст ё бинои дигар?' if tajik else 'PLAZA-I занимается архитектурным проектированием. Для какого здания нужен проект?')
    return ('Шумо дизайни дохилӣ мехоҳед, лоиҳаи меъморӣ ё назорати муаллифӣ?' if tajik else 'Вас интересует дизайн интерьера, архитектурный проект или авторский надзор?')


class AIService:
    def __init__(self, api_key: str, model: str):
        self.model=model
        self.api_key=api_key
        self.client=httpx.AsyncClient(timeout=25)

    async def reply(self, history: list[dict]) -> str:
        # Our database holds the conversation; OpenAI response storage is disabled.
        input_items=[{'role': 'assistant' if m['role'] in ('assistant','staff') else 'user',
                      'content':m['body'][:3000]} for m in history]
        response=await self.client.post('https://api.openai.com/v1/responses',
            headers={'Authorization':f'Bearer {self.api_key}',
                     'Content-Type':'application/json'},
            json={'model':self.model,'instructions':SYSTEM_PROMPT,
                  'input':input_items,'store':False,'max_output_tokens':270})
        response.raise_for_status()
        payload=response.json()
        parts=[]
        for item in payload.get('output',[]):
            if item.get('type')=='message':
                for content in item.get('content',[]):
                    if content.get('type')=='output_text':
                        parts.append(content.get('text',''))
        reply='\n'.join(parts).strip()
        if not reply:
            raise RuntimeError('Empty AI answer')
        if PRICE_OUTPUT.search(reply):
            user_text = next((m['body'] for m in reversed(history) if m['role']=='user'), '')
            reply = PRICE_REPLY_TG if is_tajik(user_text, history) else PRICE_REPLY_RU
        return reply[:3500]

    async def close(self):
        await self.client.aclose()


class WhatsAppService:
    def __init__(self, token: str, phone_number_id: str, graph_version: str):
        self.token=token
        self.url=f'https://graph.facebook.com/{graph_version}/{phone_number_id}/messages'
        self.client=httpx.AsyncClient(timeout=22)

    async def send(self, wa_id: str, text: str):
        response=await self.client.post(
            self.url,
            headers={'Authorization':f'Bearer {self.token}'},
            json={'messaging_product':'whatsapp','recipient_type':'individual',
                  'to':wa_id,'type':'text','text':{'preview_url':False,'body':text[:4096]}},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()
