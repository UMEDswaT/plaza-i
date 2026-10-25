"""Expert reference and manager-reviewed learning for PLAZA-I.

General industry guidance is not a substitute for drawings, local regulations,
engineering checks, or an approved project estimate. Client messages never
become trusted knowledge without manager review.
"""
import re
import sqlite3
import time
from contextlib import contextmanager

# category, matching expressions, Tajik guidance, Russian guidance
GUIDE = [
    ("architecture", ("меъмор", "архитект", "лоиҳа", "проект", "бино", "здание"),
     "Лоиҳакашии меъморӣ аз омӯзиши супориши техникӣ, участка ва талаботи фармоишгар оғоз мешавад. Ҳуҷҷатҳои корӣ аз навъи объект ва талаботи қонунгузории амалкунанда вобастаанд.",
     "Архитектурное проектирование начинается с технического задания, участка и требований заказчика. Рабочая документация зависит от типа объекта и действующих требований."),
    ("stages", ("марҳила", "эскиз", "генплан", "планировка", "стадии", "концепц"),
     "Марҳилаҳои маъмул: супориши техникӣ, таҳлили қитъа, консепсия ва эскиз, таҳияи қисмҳои лоиҳа, мувофиқаҳои зарурӣ ва ҳуҷҷатҳои корӣ. Ҳайати воқеии марҳилаҳоро шартнома муайян мекунад.",
     "Типовые этапы: техническое задание, анализ участка, концепция и эскиз, разделы проекта, необходимые согласования и рабочая документация. Точный состав определяется договором."),
    ("site", ("участ", "қитъа", "геодез", "геолог", "рельеф", "топосъемк"),
     "Пеш аз тарҳрезии ҷиддӣ маълумоти қитъа, андозаҳо, релеф, дастрасӣ, шабакаҳои муҳандисӣ ва таҳқиқоти зарурӣ санҷида мешаванд. Замин ва борбардории таҳкурсиро муҳандиси соҳавӣ арзёбӣ мекунад.",
     "Перед проектированием проверяют параметры участка, рельеф, подъезд, инженерные сети и необходимые изыскания. Грунты и основания оценивает профильный инженер."),
    ("estimate", ("смет", "хароҷот", "расход", "бюджет", "калькуляц", "стоимост", "арзиш"),
     "Смета аз ҳаҷми корҳо, воҳиди ченак, миқдор, нархи мавод, меҳнат, техника, хароҷоти иловагӣ ва захираи эҳтимолӣ таркиб меёбад. Барои маблағи боэътимод андозаҳо, нақшаҳо ва нархҳои ҷории маҳаллӣ заруранд; нархи тахминӣ бе онҳо дода намешавад.",
     "Смета учитывает объёмы работ, единицы, количество, материалы, труд, механизмы, накладные расходы и резерв. Для надёжной суммы нужны замеры, чертежи и актуальные местные цены; без них конкретную стоимость не назначают."),
    ("bill_of_quantities", ("ведомост", "ҳаҷми кор", "объем работ", "материал", "масолеҳ", "boq"),
     "Ведомости ҳаҷми корҳо (BOQ) рӯйхати корҳои сохтмонӣ бо воҳид ва миқдор аст. Онро аз нақшаҳои мувофиқашуда ва ченкуниҳо месозанд; миқдори пешакӣ бояд санҷида шавад.",
     "Ведомость объёмов работ (BOQ) содержит виды работ, единицы измерения и количества. Её составляют по согласованным чертежам и обмерам; предварительные количества проверяются."),
    ("interior", ("интерьер", "дизайн", "хона", "квартира", "офис", "утоқ"),
     "Дизайни дохилӣ банақшагирӣ, эргономика, рӯшноӣ, мавод, ранг, мебел ва нақшаҳои кориро фаро мегирад. Пеш аз интихоби услуб, масоҳат ва вазифаи ҳар ҳуҷра муайян мешавад.",
     "Дизайн интерьера охватывает планировку, эргономику, освещение, материалы, цвет, мебель и рабочие чертежи. Сначала уточняются площадь и назначение помещений."),
    ("styles", ("минимал", "классик", "лофт", "скандинав", "муосир", "современ", "неокласс"),
     "Минимализм шаклҳои содда ва функсионалӣ; классика таносуб ва ҷузъиёти анъанавӣ; лофт маводи намоён ва фазои кушод; услуби скандинавӣ равшанӣ ва ҳалли амалӣ дорад. Интихоб аз завқ, масоҳат ва буҷет вобаста аст.",
     "Минимализм — простые функциональные формы; классика — пропорции и традиционные детали; лофт — открытые фактуры; скандинавский стиль — светлые практичные решения. Выбор зависит от задачи и бюджета."),
    ("visualization", ("визуализ", "рендер", "3d", "3д", "модел", "эскиз"),
     "3D-визуализатсия намуди пешбинишудаи тарҳро нишон медиҳад. Расми 3D ҷойгузини нақшаҳои дақиқи корӣ, конструктивӣ ва иҷозатнома нест.",
     "3D-визуализация показывает предполагаемый облик проекта, но не заменяет рабочие чертежи, конструктивные расчёты или согласования."),
    ("author_supervision", ("назорати муаллиф", "авторск", "авторский надзор"),
     "Назорати муаллифӣ мутобиқати корҳои иҷрошавандаро ба қарорҳои лоиҳавии тасдиқшуда месанҷад ва тағйироти лоиҳаро мувофиқа мекунад. Он ҷойгузини назорати техникии сохтмон ё масъулияти пудратчӣ нест.",
     "Авторский надзор проверяет соответствие выполняемых работ утверждённым проектным решениям и согласует проектные изменения. Он не заменяет технический надзор или ответственность подрядчика."),
    ("technical_supervision", ("технадзор", "назорати техник", "технический надзор"),
     "Назорати техникӣ сифати кор, ҳуҷҷатҳои иҷро ва риояи талаботи сохтмонро мувофиқи салоҳият месанҷад; нақши он аз назорати муаллифӣ фарқ мекунад.",
     "Технический надзор проверяет качество работ и исполнительную документацию в пределах своих полномочий; это не то же самое, что авторский надзор."),
    ("engineering", ("конструк", "муҳандис", "инженер", "электр", "вентиляц", "сантех", "отоплен"),
     "Қисмҳои конструктивӣ ва муҳандисӣ метавонанд ҳисобҳои борбардорӣ, электрикӣ, обтаъминкунӣ, канализатсия, гармидиҳӣ ва вентилятсияро талаб кунанд. Қарорҳои бехатарӣ аз ҷониби мутахассисони соҳибихтисос санҷида мешаванд.",
     "Конструктивные и инженерные разделы могут включать расчёты нагрузок, электрику, воду, канализацию, отопление и вентиляцию. Безопасность решений проверяют профильные специалисты."),
    ("permits", ("иҷозат", "разрешен", "лицензи", "меъёр", "норма", "қонун", "снип"),
     "Талаботи иҷозат, меъёрҳои маҳаллӣ ва доираи литсензия вобаста ба объект ва ҷойи сохтмон фарқ мекунанд. Ҳуҷҷати расмӣ ва мутахассиси масъул бояд версияи амалкунандаро тасдиқ кунад.",
     "Разрешения, местные нормы и объём лицензии зависят от объекта и площадки. Актуальные требования необходимо проверить по официальным документам и с ответственным специалистом."),
    ("renovation", ("таъмир", "ремонт", "перепланиров", "реконструк", "азнавсоз"),
     "Ҳангоми таъмир ё азнавбанақшагирӣ андозаҳои воқеӣ, конструксияҳои борбардор ва шабакаҳо санҷида мешаванд. Дахолат ба унсурҳои борбардор бе муҳандиси масъул тавсия намешавад.",
     "При ремонте и перепланировке проверяют обмеры, несущие конструкции и сети. Изменения несущих элементов требуют профильной инженерной проверки."),
    ("contract", ("шартнома", "договор", "натиҷаи кор", "комплект", "чертеж"),
     "Дар шартномаи лоиҳакашӣ беҳтар аст натиҷаҳои супоридашаванда, шумораи ислоҳҳо, марҳилаҳо, масъулиятҳо ва тартиби қабули кор дақиқ сабт шаванд.",
     "В договоре проектирования следует закрепить состав выдаваемых материалов, количество правок, этапы, обязанности и порядок приёмки."),
    ("safety", ("эвакуат", "пожар", "зилзила", "сейсм", "безопасн", "бехатар"),
     "Барои бехатарии сӯхтор, эвакуатсия ва устувории сейсмикӣ санҷиши мутахассис ва меъёрҳои амалкунандаи маҳаллӣ зарур аст. Бот наметавонад хулосаи муҳандисии тасдиқшуда диҳад.",
     "Для пожарной безопасности, эвакуации и сейсмостойкости нужны профильные расчёты и актуальные местные нормы. Бот не выдаёт утверждённое инженерное заключение."),
]


def matching_guides(query: str, limit: int = 3):
    q = query.casefold()
    scored = []
    for topic, words, tg, ru in GUIDE:
        score = sum(2 if w in q else 0 for w in words)
        if score:
            scored.append((score, topic, tg, ru))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(topic, tg, ru) for _, topic, tg, ru in scored[:limit]]


def reference_for(query: str) -> str:
    notes = matching_guides(query, limit=3)
    return "\n".join(f"[{key}] TG: {tg} RU: {ru}" for key, tg, ru in notes)[:3400]


def domain_demo_reply(message: str, tajik: bool):
    q = message.casefold()
    guide = matching_guides(q, limit=1)
    if not guide:
        return None
    key, tg, ru = guide[0]
    # For broad interior/architecture terms the existing conversational flow
    # is more useful; prefer reference answers for specialist questions.
    if key in ("interior", "architecture") and len(q) < 55:
        return None
    return tg if tajik else ru


PII = re.compile(
    r"(?i)(?:[\w.+-]+@[\w.-]+\.[a-z]{2,}|https?://\S+|"
    r"(?:\+?\d[\d\s()\-]{6,}\d)|@\w+|\b\d{4,}\b)"
)
TOKEN = re.compile(r"[^\W_]{3,}", re.UNICODE)


def contains_sensitive(text: str) -> bool:
    return bool(PII.search(text))


def normalized_words(text: str):
    return set(TOKEN.findall(text.casefold()))


class KnowledgeBase:
    """SQLite knowledge with mandatory human approval and no model fine-tuning."""

    def __init__(self, path: str):
        self.path = path
        with self.db() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_entries(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic TEXT NOT NULL,
                  question TEXT NOT NULL,
                  answer TEXT NOT NULL,
                  state TEXT NOT NULL DEFAULT 'pending'
                    CHECK (state IN ('pending','approved','rejected')),
                  origin TEXT NOT NULL,
                  created REAL NOT NULL,
                  modified REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS knowledge_state ON knowledge_entries(state,id);
            """)

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def validated(question: str, answer: str):
        question, answer = question.strip(), answer.strip()
        if not (8 <= len(question) <= 500 and 10 <= len(answer) <= 1500):
            raise ValueError("Question or answer length is invalid")
        if contains_sensitive(question) or contains_sensitive(answer):
            raise ValueError("Remove personal contact details, links and long identifiers")
        return question, answer

    def propose(self, question: str, answer: str, topic="general", origin="manager"):
        question, answer = self.validated(question, answer)
        with self.db() as con:
            duplicate = con.execute(
                "SELECT id FROM knowledge_entries WHERE lower(question)=lower(?) "
                "AND lower(answer)=lower(?) AND state!='rejected' LIMIT 1",
                (question, answer)).fetchone()
            if duplicate:
                return duplicate["id"]
            stamp = time.time()
            result = con.execute(
                "INSERT INTO knowledge_entries(topic,question,answer,origin,created,modified) "
                "VALUES(?,?,?,?,?,?)",
                (topic[:60], question, answer, origin[:35], stamp, stamp))
            return result.lastrowid

    def suggest_from_staff(self, question: str, answer: str):
        # Only managers' authored replies create drafts, never AI/client assertions.
        # Reject customer-specific exchanges rather than storing unredacted PII.
        try:
            return self.propose(question, answer, "from_staff", "staff_reply")
        except ValueError:
            return None

    def list_entries(self, state: str = "all", limit: int = 100):
        if state not in ("all", "pending", "approved", "rejected"):
            raise ValueError("Invalid review filter")
        with self.db() as con:
            if state == "all":
                rows = con.execute(
                    "SELECT * FROM knowledge_entries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM knowledge_entries WHERE state=? ORDER BY id DESC LIMIT ?",
                    (state, limit)).fetchall()
            return [dict(row) for row in rows]

    def review(self, entry_id: int, state: str, question=None, answer=None):
        if state not in ("approved", "rejected"):
            raise ValueError("Invalid review state")
        with self.db() as con:
            row = con.execute("SELECT * FROM knowledge_entries WHERE id=?", (entry_id,)).fetchone()
            if row is None:
                raise KeyError(entry_id)
            new_question = row["question"] if question is None else question
            new_answer = row["answer"] if answer is None else answer
            new_question, new_answer = self.validated(new_question, new_answer)
            con.execute(
                "UPDATE knowledge_entries SET question=?,answer=?,state=?,modified=? WHERE id=?",
                (new_question, new_answer, state, time.time(), entry_id))

    def search_approved(self, query: str, limit: int = 3):
        words = normalized_words(query)
        if not words:
            return []
        with self.db() as con:
            rows = con.execute(
                "SELECT id,topic,question,answer FROM knowledge_entries "
                "WHERE state='approved' ORDER BY id DESC LIMIT 500").fetchall()
        ranked = []
        for row in rows:
            qwords = normalized_words(row["question"])
            awords = normalized_words(row["answer"])
            score = 4 * len(words & qwords) + len(words & awords)
            if query.casefold().strip() == row["question"].casefold().strip():
                score += 20
            if score >= 4:
                ranked.append((score, dict(row)))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in ranked[:limit]]

    def context(self, query: str) -> str:
        relevant = self.search_approved(query)
        approved = "\n".join(
            f"Approved Q: {r['question']}\nApproved A: {r['answer']}"
            for r in relevant
        )[:2600]
        return (reference_for(query) + "\n\nMANAGER-APPROVED ANSWERS:\n" + approved).strip()[:6000]

    def demo_answer(self, query: str):
        results = self.search_approved(query, limit=1)
        if results and normalized_words(query) & normalized_words(results[0]["question"]):
            return results[0]["answer"]
        return None
