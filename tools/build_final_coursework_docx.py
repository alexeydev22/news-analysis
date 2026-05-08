from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "docs" / "final"
ASSETS_DIR = FINAL_DIR / "assets"
DOCX_PATH = FINAL_DIR / "coursework-explanatory-note.docx"

UNIVERSITY = "Финансовый университет при Правительстве РФ"
STUDENT = "Прудиев Алексей Сергеевич"
GROUP = "ПМ23-4"
YEAR = "2026"

BLUE = "1F3A5F"
ACCENT = "0F5132"
INK = "111111"
MUTED = "4F5B57"
GRID = "B7C6C0"
TABLE_HEADER = "E8EEF5"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str, outline: str | None = None, radius: int = 16, width: int = 2) -> None:
    fill = fill if fill.startswith("#") else f"#{fill}"
    outline = None if outline is None else outline if outline.startswith("#") else f"#{outline}"
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def build_architecture_diagram() -> Path:
    path = ASSETS_DIR / "architecture-diagram.png"
    img = Image.new("RGB", (1800, 1050), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    title_font = font(46, True)
    label_font = font(28, True)
    body_font = font(22)
    small_font = font(18)

    draw.text((70, 50), "Архитектура диалоговой системы анализа экономических новостей", fill=f"#{INK}", font=title_font)
    draw.text((72, 112), "Баланс ML/NLP pipeline и production backend: поиск, анализ влияния, генерация ответа и интерфейс", fill=f"#{MUTED}", font=body_font)

    boxes = {
        "ui": (70, 220, 360, 360, "frontend-web", "React-интерфейс"),
        "news": (70, 520, 360, 660, "news-service", "CSV preview/index"),
        "gateway": (500, 260, 820, 400, "api-gateway", "FastAPI + SSE"),
        "worker": (500, 560, 820, 700, "news-worker", "Taskiq worker"),
        "retrieval": (960, 170, 1270, 310, "retrieval-service", "поиск в Qdrant"),
        "analysis": (960, 390, 1270, 530, "analysis-service", "оценка влияния"),
        "dialog": (960, 610, 1270, 750, "dialog-service", "template / LLM"),
        "qdrant": (1430, 170, 1710, 310, "Qdrant", "векторное хранилище"),
        "redis": (1430, 450, 1710, 590, "Redis", "очередь и события"),
        "mlflow": (1430, 730, 1710, 870, "MLflow", "эксперименты"),
    }

    for key, (x1, y1, x2, y2, title, subtitle) in boxes.items():
        fill = "EAF4EF" if key in {"ui", "gateway"} else "F8FAF9"
        outline = ACCENT if key in {"ui", "gateway"} else GRID
        rounded_rect(draw, (x1, y1, x2, y2), f"#{fill}", f"#{outline}", radius=18, width=3)
        draw.text((x1 + 24, y1 + 28), title, fill=f"#{INK}", font=label_font)
        draw.text((x1 + 24, y1 + 78), subtitle, fill=f"#{MUTED}", font=body_font)

    def arrow_path(points: list[tuple[int, int]], label: str = "") -> None:
        draw.line(points, fill=f"#{ACCENT}", width=4, joint="curve")
        start = points[-2]
        end = points[-1]
        ex, ey = end
        sx, sy = start
        if abs(ex - sx) >= abs(ey - sy) and ex >= sx:
            pts = [(ex, ey), (ex - 16, ey - 9), (ex - 16, ey + 9)]
        elif abs(ex - sx) >= abs(ey - sy):
            pts = [(ex, ey), (ex + 16, ey - 9), (ex + 16, ey + 9)]
        elif ey >= sy:
            pts = [(ex, ey), (ex - 9, ey - 16), (ex + 9, ey - 16)]
        else:
            pts = [(ex, ey), (ex - 9, ey + 16), (ex + 9, ey + 16)]
        draw.polygon(pts, fill=f"#{ACCENT}")
        if label:
            middle = points[len(points) // 2]
            lx = middle[0] - 42
            ly = middle[1] - 30
            draw.text((lx, ly), label, fill=f"#{MUTED}", font=small_font)

    arrow_path([(360, 290), (500, 330)], "chat")
    arrow_path([(215, 360), (215, 520)], "CSV")
    arrow_path([(360, 590), (500, 630)], "jobs")
    arrow_path([(820, 310), (960, 240)], "search")
    arrow_path([(820, 330), (960, 460)], "analyze")
    arrow_path([(820, 350), (900, 350), (900, 680), (960, 680)], "answer")
    arrow_path([(1270, 240), (1430, 240)], "vectors")
    arrow_path([(820, 630), (900, 630), (900, 300), (960, 240)], "index")
    arrow_path([(820, 660), (1430, 520)], "queue")
    arrow_path([(1270, 460), (1350, 460), (1350, 800), (1430, 800)], "metrics")

    footer = "Сценарий: CSV -> текстовые признаки и embeddings -> retrieval -> классификация влияния -> ответ с источниками"
    draw.text((70, 940), footer, fill=f"#{MUTED}", font=body_font)
    img.save(path)
    return path


def build_ui_mock() -> Path:
    path = ASSETS_DIR / "ui-demo-screenshot.png"
    img = Image.new("RGB", (1800, 1050), "#F7FAF8")
    draw = ImageDraw.Draw(img)
    title_font = font(36, True)
    h_font = font(26, True)
    body_font = font(22)
    small_font = font(18)

    draw.rectangle((0, 0, 1800, 1050), fill="#F7FAF8")
    draw.rectangle((0, 0, 380, 1050), fill="#EEF5F1")
    draw.line((380, 0, 380, 1050), fill="#D1DED8", width=2)
    draw.line((1330, 0, 1330, 1050), fill="#D1DED8", width=2)

    draw.text((60, 70), "Диалоговая\nсистема", fill=f"#{INK}", font=title_font, spacing=8)
    draw.text((60, 210), "Модель анализа", fill=f"#{MUTED}", font=body_font)
    rounded_rect(draw, (60, 248, 330, 300), "FFFFFF", "B9CAC2", radius=8)
    draw.text((82, 260), "tfidf-logreg", fill=f"#{INK}", font=body_font)
    draw.text((60, 340), "Лимит источников", fill=f"#{MUTED}", font=body_font)
    rounded_rect(draw, (60, 378, 330, 430), "FFFFFF", "B9CAC2", radius=8)
    draw.text((82, 390), "5", fill=f"#{INK}", font=body_font)
    rounded_rect(draw, (60, 490, 210, 545), ACCENT, ACCENT, radius=8)
    draw.text((76, 505), "Предпросмотр", fill="#FFFFFF", font=small_font)
    rounded_rect(draw, (225, 490, 345, 545), ACCENT, ACCENT, radius=8)
    draw.text((242, 505), "Индекс", fill="#FFFFFF", font=small_font)
    draw.text((60, 610), "Набор данных", fill=f"#{INK}", font=h_font)
    draw.text((60, 655), "5 русскоязычных\nэкономических новостей", fill=f"#{INK}", font=body_font, spacing=8)

    draw.text((430, 70), "Вопрос", fill=f"#{MUTED}", font=body_font)
    rounded_rect(draw, (430, 108, 1285, 230), "FFFFFF", "B9CAC2", radius=10)
    draw.text((455, 128), "Что означает рост ВВП и снижение инфляции для рынка?", fill=f"#{INK}", font=body_font)
    rounded_rect(draw, (430, 255, 520, 310), ACCENT, ACCENT, radius=8)
    draw.text((456, 270), "Ask", fill="#FFFFFF", font=body_font)

    answer = (
        "По вопросу найдены релевантные новости. Рост ВВП обычно указывает на "
        "расширение экономической активности, а снижение инфляции уменьшает "
        "давление на ставку и поддерживает ожидания рынка. Итоговая оценка "
        "строится на найденных источниках и не является финансовой рекомендацией."
    )
    rounded_rect(draw, (430, 330, 1285, 560), "FFFFFF", "D5E1DC", radius=10)
    y = 355
    for line in wrap_text(draw, answer, body_font, 790):
        draw.text((455, y), line, fill=f"#{INK}", font=body_font)
        y += 33

    draw.text((430, 610), "Ход обработки", fill=f"#{INK}", font=h_font)
    events = ["chat_started", "search_started", "sources_found", "analysis_started", "analysis_completed", "answer_started", "answer_completed", "done"]
    y = 655
    for index, event in enumerate(events, start=1):
        draw.text((470, y), f"{index}. {event}", fill=f"#{INK}", font=body_font)
        y += 32

    draw.text((1370, 70), "Источники", fill=f"#{INK}", font=h_font)
    source_cards = [
        ("Центральный банк сохранил ставку", "Central Bank Brief", "score 0.79", "нейтральное"),
        ("ВВП вырос быстрее ожиданий", "demo", "score 0.78", "позитивное"),
        ("Безработица остается низкой", "Labor Statistics", "score 0.76", "нейтральное"),
        ("Экспортные заказы сократились", "Trade Monitor", "score 0.72", "негативное"),
    ]
    y = 125
    for title, src, score, impact in source_cards:
        rounded_rect(draw, (1370, y, 1750, y + 175), "FFFFFF", "D5E1DC", radius=12)
        draw.text((1390, y + 22), title, fill=f"#{INK}", font=small_font)
        draw.text((1390, y + 58), src, fill=f"#{INK}", font=small_font)
        draw.text((1390, y + 94), score, fill=f"#{MUTED}", font=small_font)
        draw.text((1390, y + 130), impact, fill=f"#{ACCENT}", font=small_font)
        y += 200

    img.save(path)
    return path


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
    run.font.size = Pt(12)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, True)
        set_cell_shading(table.rows[0].cells[index], TABLE_HEADER)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            set_cell_text(cells[index], value)
    doc.add_paragraph()


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def add_numbers(doc: Document, items: list[str]) -> None:
    for index, item in enumerate(items, start=1):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.left_indent = Cm(0.75)
        paragraph.paragraph_format.line_spacing = 1.5
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(f"{index}. {item}")
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
        run.font.size = Pt(14)


def configure_doc(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
    normal.font.size = Pt(14)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color, before, after in [
        ("Title", 16, INK, 0, 12),
        ("Heading 1", 14, INK, 18, 8),
        ("Heading 2", 14, INK, 12, 6),
        ("Heading 3", 14, INK, 10, 4),
    ]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    header = section.header.paragraphs[0]
    header.text = "Курсовая работа"
    header.runs[0].font.name = "Times New Roman"
    header.runs[0].font.size = Pt(10)
    header.runs[0].font.color.rgb = RGBColor.from_string(MUTED)

    footer = section.footer.paragraphs[0]
    footer.text = f"{STUDENT}, {GROUP}"
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.runs[0].font.name = "Times New Roman"
    footer.runs[0].font.size = Pt(10)
    footer.runs[0].font.color.rgb = RGBColor.from_string(MUTED)


def build_docx() -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    arch = build_architecture_diagram()
    ui = build_ui_mock()

    doc = Document()
    configure_doc(doc)

    org = doc.add_paragraph()
    org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    org.paragraph_format.first_line_indent = Cm(0)
    org.add_run(UNIVERSITY).bold = True

    for _ in range(7):
        doc.add_paragraph()

    work_type = doc.add_paragraph()
    work_type.alignment = WD_ALIGN_PARAGRAPH.CENTER
    work_type.paragraph_format.first_line_indent = Cm(0)
    work_type.add_run("КУРСОВАЯ РАБОТА").bold = True

    discipline = doc.add_paragraph()
    discipline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    discipline.paragraph_format.first_line_indent = Cm(0)
    discipline.add_run("по дисциплине: ____________________")

    topic = doc.add_paragraph()
    topic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    topic.paragraph_format.first_line_indent = Cm(0)
    topic.add_run("на тему: «Разработка автоматической диалоговой системы на основе языковой модели для анализа экономических новостей»").bold = True

    for _ in range(5):
        doc.add_paragraph()

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    meta.paragraph_format.first_line_indent = Cm(0)
    meta.add_run(f"Выполнил: {STUDENT}\nГруппа: {GROUP}\nРуководитель: ____________________")

    for _ in range(8):
        doc.add_paragraph()

    year = doc.add_paragraph()
    year.alignment = WD_ALIGN_PARAGRAPH.CENTER
    year.paragraph_format.first_line_indent = Cm(0)
    year.add_run(f"Москва, {YEAR}")

    doc.add_page_break()
    doc.add_heading("СОДЕРЖАНИЕ", level=1)
    add_numbers(doc, [
        "Введение",
        "Анализ предметной области",
        "Проектирование диалоговой системы",
        "Реализация программного проекта",
        "Тестирование и демонстрация результатов",
        "Заключение",
        "Список использованных источников",
    ])

    doc.add_heading("ВВЕДЕНИЕ", level=1)
    for para in [
        "Экономические новости ежедневно влияют на ожидания инвесторов, компаний, потребителей и государственных органов. Рост ВВП, изменение инфляции, решения центральных банков, динамика безработицы и торговые показатели могут менять оценку рыночных рисков.",
        "Автоматические диалоговые системы позволяют упростить работу с такими данными: пользователь формулирует вопрос естественным языком, а система находит релевантные источники, анализирует их и формирует краткий ответ.",
        "Работа находится на стыке машинного обучения и backend-разработки. ML/NLP-часть отвечает за текстовое представление новостей, поиск релевантного контекста, классификацию влияния и подключение языковой модели. Инженерная часть отвечает за микросервисную архитектуру, асинхронную обработку, веб-интерфейс и воспроизводимый запуск.",
        "Объектом работы являются экономические новости. Предметом работы являются методы построения автоматической диалоговой системы для поиска, анализа и обобщения экономических новостей.",
        "Цель работы: разработать локальную автоматическую диалоговую систему, которая принимает вопрос пользователя, находит релевантные экономические новости, оценивает их влияние и формирует ответ на основе найденных источников.",
    ]:
        doc.add_paragraph(para)
    doc.add_paragraph("Для достижения цели поставлены задачи:")
    add_numbers(doc, [
        "Изучить предметную область анализа экономических новостей.",
        "Определить ML/NLP pipeline: представление текста, поиск, классификация влияния и генерация ответа.",
        "Спроектировать микросервисную архитектуру диалоговой системы.",
        "Реализовать сервис загрузки и индексации новостей.",
        "Реализовать сервис векторного поиска релевантных новостей.",
        "Реализовать сервис анализа влияния новости.",
        "Реализовать сервис генерации ответа с поддержкой языковой модели.",
        "Реализовать веб-интерфейс для работы пользователя.",
        "Подготовить воспроизводимый сценарий запуска и проверки.",
    ])

    doc.add_heading("1. АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ", level=1)
    for para in [
        "Экономические новости представляют собой текстовые сообщения о событиях, которые могут влиять на рынок, отрасли и отдельные компании. Такие события часто связаны с макроэкономическими показателями, монетарной политикой, торговлей, занятостью и промышленностью.",
        "С точки зрения машинного обучения задача включает несколько подзадач обработки естественного языка: нормализацию и представление текста, поиск релевантных документов, классификацию влияния новости и генерацию итогового ответа. Поэтому система должна не только отдавать HTTP-ответ, но и выполнять понятный ML/NLP pipeline.",
        "Для классификации влияния новости применяется воспроизводимый baseline tfidf-logreg. Такой подход хорошо подходит для учебной защиты: он объясним, быстро запускается локально и показывает связь между текстовыми признаками и итоговым классом влияния. В архитектуре также предусмотрены режимы на embeddings и небольшой transformer-модели.",
        "Retrieval-подход позволяет сначала найти контекст, а затем формировать ответ на основе найденных документов. Это снижает риск абстрактного ответа и делает результат объяснимым для пользователя.",
    ]:
        doc.add_paragraph(para)
    add_table(doc, ["ML/NLP-задача", "Роль в системе"], [
        ["Текстовое представление", "TF-IDF и embeddings используются для поиска и классификации новостей."],
        ["Retrieval", "Поиск релевантных документов формирует контекст для ответа."],
        ["Классификация влияния", "Модель определяет позитивное, негативное или нейтральное влияние новости."],
        ["Генерация ответа", "Dialog-service собирает ответ по найденным источникам через template или LLM-режим."],
        ["ML tracking", "MLflow предусмотрен для фиксации экспериментов и артефактов моделей."],
    ])

    doc.add_heading("2. ПРОЕКТИРОВАНИЕ ДИАЛОГОВОЙ СИСТЕМЫ", level=1)
    doc.add_paragraph("Система построена как локальный микросервисный стенд. Такой подход разделяет ответственность компонентов и позволяет показать полный pipeline обработки вопроса.")
    doc.add_picture(str(arch), width=Inches(6.3))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption = doc.add_paragraph("Рисунок 1 - Архитектура диалоговой системы")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.first_line_indent = Cm(0)
    add_table(doc, ["Компонент", "Ответственность"], [
        ["frontend-web", "Веб-интерфейс чата, предпросмотра CSV и отображения источников."],
        ["api-gateway", "Единая точка входа, оркестрация поиска, анализа и генерации ответа."],
        ["news-service", "Предпросмотр CSV и запуск индексации новостей."],
        ["news-worker", "Фоновая индексация через Taskiq и Redis."],
        ["retrieval-service", "Индексация документов и поиск релевантных новостей в Qdrant."],
        ["analysis-service", "Классификация влияния новости."],
        ["dialog-service", "Формирование итогового ответа через template или LLM-режим."],
    ])
    doc.add_paragraph("Backend-сервисы используют слоистую архитектуру: domain, application, infrastructure, presentation и main. Интерфейсы портов описаны через Protocol, а зависимости собираются через Dishka. Такое разделение сохраняет ясную границу между ML-логикой, доменными правилами и инфраструктурными адаптерами.")

    doc.add_heading("3. РЕАЛИЗАЦИЯ ПРОГРАММНОГО ПРОЕКТА", level=1)
    for para in [
        "Проект реализован в формате monorepo. Backend написан на Python с использованием FastAPI, asyncio и Granian. Межсервисные HTTP-вызовы выполняются через Zapros, настройки описываются через Pydantic Settings, структурные логи формируются через structlog.",
        "Фоновые задачи вынесены в news-worker. Taskiq ставит задачи индексации, Redis используется как backend очереди, а FastStream публикует события. Этот вариант легче RabbitMQ и подходит для локального стенда.",
        "Векторный поиск реализован через Qdrant. Для demo-режима поддерживаются статические embeddings, чтобы запуск не зависел от скачивания внешней модели.",
        "ML/NLP-часть выделена в отдельные контракты и сервисы. Analysis-service получает текст новости, применяет выбранный режим анализа и возвращает класс влияния, confidence score и краткое объяснение на русском языке.",
        "Основной demo-режим tfidf-logreg выбран как объяснимый baseline. Он дополняется предусмотренными режимами embedding-logreg и tiny-transformer-classifier, чтобы в дальнейшем можно было сравнивать качество разных подходов без изменения внешнего API.",
        "Dialog-service поддерживает template fallback и LLM-режим через OpenAI-compatible локальный сервер. Для легкого локального варианта предусмотрена модель Qwen3-0.6B-Instruct-GGUF через llama.cpp.",
    ]:
        doc.add_paragraph(para)
    add_table(doc, ["Часть", "Технологии"], [
        ["ML: признаки текста", "TF-IDF, статические embeddings"],
        ["ML: классификация", "Logistic Regression baseline, режимы embedding-logreg и tiny-transformer-classifier"],
        ["NLP: retrieval/RAG", "Qdrant, поиск контекста, ответ по источникам"],
        ["NLP: генерация", "Template fallback, OpenAI-compatible LLM через llama.cpp"],
        ["ML tracking", "MLflow"],
        ["Backend", "FastAPI, asyncio, Granian, Zapros"],
        ["Архитектура", "DDD, слои, Protocol, Dishka"],
        ["Фоновые задачи и события", "Taskiq, Redis, FastStream"],
        ["Frontend и запуск", "React, Docker Compose, Dockerfile, Justfile"],
    ])

    doc.add_heading("4. ТЕСТИРОВАНИЕ И ДЕМОНСТРАЦИЯ РЕЗУЛЬТАТОВ", level=1)
    doc.add_paragraph("Для проверки проекта подготовлены unit-тесты, тесты контрактов, API-тесты, frontend-тесты и demo smoke-сценарий. Проверка охватывает как инженерную связность сервисов, так и корректность ML/NLP-сценария: поиск источников, классификацию влияния и формирование ответа по найденному контексту.")
    add_table(doc, ["Проверка", "Назначение"], [
        ["git diff --check", "Проверка форматных ошибок в diff."],
        ["docker compose config --quiet", "Проверка корректности compose-конфигурации."],
        ["just demo-smoke", "Проверка health endpoints, CSV preview, индексации, фоновой задачи, SSE и frontend."],
        ["frontend tests", "Проверка React UI и клиентских API."],
        ["ML/NLP demo", "Проверка найденных источников, score, класса влияния и итогового ответа."],
    ])
    doc.add_picture(str(ui), width=Inches(6.3))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption = doc.add_paragraph("Рисунок 2 - Интерфейс демонстрационного сценария")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.first_line_indent = Cm(0)
    doc.add_paragraph("Ручной сценарий демонстрации: запустить just demo-up, открыть http://localhost:5173, выполнить предпросмотр CSV, индексировать новости и задать вопрос о росте ВВП и снижении инфляции.")

    doc.add_heading("ЗАКЛЮЧЕНИЕ", level=1)
    for para in [
        "В ходе работы была разработана локальная микросервисная диалоговая система для анализа экономических новостей. Система принимает вопрос пользователя, ищет релевантные новости, классифицирует их влияние и формирует ответ с указанием источников.",
        "Содержательно работа сбалансирована между машинным обучением и backend-разработкой. ML/NLP-результат включает retrieval pipeline, классификацию влияния, поддержку разных режимов анализа и LLM-адаптер. Инженерный результат включает микросервисную архитектуру, асинхронные сервисы, фоновые задачи, SSE-интерфейс и воспроизводимый Docker Compose запуск.",
        "Поставленная цель достигнута. Проект соответствует теме курсовой работы, поскольку реализует автоматический диалоговый сценарий на основе найденного контекста, анализа экономических новостей и подключаемой языковой модели.",
        "Дальнейшее развитие может включать подключение реальных новостных API, сохранение истории диалогов в PostgreSQL, обучение дополнительных моделей анализа и сравнение качества template и LLM-режимов.",
    ]:
        doc.add_paragraph(para)

    doc.add_heading("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", level=1)
    add_numbers(doc, [
        "FastAPI Documentation. https://fastapi.tiangolo.com/",
        "Granian Documentation. https://github.com/emmett-framework/granian",
        "Pydantic Documentation. https://docs.pydantic.dev/",
        "Dishka Documentation. https://dishka.readthedocs.io/",
        "Taskiq Documentation. https://taskiq-python.github.io/",
        "FastStream Documentation. https://faststream.ag2.ai/",
        "Redis Documentation. https://redis.io/docs/",
        "Qdrant Documentation. https://qdrant.tech/documentation/",
        "MLflow Documentation. https://mlflow.org/docs/latest/",
        "React Documentation. https://react.dev/",
        "Docker Compose Documentation. https://docs.docker.com/compose/",
        "Evans E. Domain-Driven Design: Tackling Complexity in the Heart of Software.",
        "Lewis P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.",
        "Vaswani A. et al. Attention Is All You Need.",
    ])

    doc.save(DOCX_PATH)
    return DOCX_PATH


if __name__ == "__main__":
    result = build_docx()
    print(result)
