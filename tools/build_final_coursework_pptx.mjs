import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");

const root = process.cwd();
const finalDir = path.join(root, "docs", "final");
const assetsDir = path.join(finalDir, "assets");
const factsPath = path.join(finalDir, "source", "materials-facts.json");
const templatePath = path.join(root, "PrezaFin_shablon-arial_itog.pptx");
const pptxPath = path.join(finalDir, "coursework-defense-presentation.pptx");
const facts = JSON.parse(fs.readFileSync(factsPath, "utf8"));
fs.accessSync(templatePath, fs.constants.R_OK);

const STUDENT = facts.student.name;
const GROUP = facts.student.group;
const UNIVERSITY = facts.student.university;
const FONT = "Times New Roman";
const TOTAL_SLIDES = 15;

const pptx = new pptxgen();
pptx.author = STUDENT;
pptx.subject = "Курсовая работа";
pptx.title = facts.coursework.topic;
pptx.company = UNIVERSITY;
pptx.lang = "ru-RU";
pptx.theme = {
  headFontFace: FONT,
  bodyFontFace: FONT,
  lang: "ru-RU",
};
pptx.defineLayout({ name: "COURSE", width: 13.333, height: 7.5 });
pptx.layout = "COURSE";

const C = {
  bg: "F8F9F8",
  ink: "111111",
  muted: "4F5B57",
  green: "0F5132",
  light: "EDF3F0",
  grid: "B7C6C0",
  blue: "1F3A5F",
  white: "FFFFFF",
  warn: "F6F1E8",
};

function addFooter(slide, n) {
  slide.addText(`${STUDENT} · ${GROUP} · ${n}/${TOTAL_SLIDES}`, {
    x: 0.55, y: 7.08, w: 12.2, h: 0.22,
    fontFace: FONT, fontSize: 8.5, color: C.muted, align: "right",
    margin: 0,
  });
}

function addTitle(slide, text, subtitle, n) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.green }, line: { color: C.green } });
  slide.addText(text, {
    x: 0.65, y: 0.42, w: 11.6, h: 0.55,
    fontFace: FONT, fontSize: 24, bold: true, color: C.ink,
    margin: 0, fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.67, y: 1.05, w: 11.1, h: 0.35,
      fontFace: FONT, fontSize: 12, color: C.muted,
      margin: 0, fit: "shrink",
    });
  }
  addFooter(slide, n);
}

function sectionLabel(slide, text, x, y, w = 2.5) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h: 0.32,
    fill: { color: C.green },
    line: { color: C.green },
  });
  slide.addText(text, {
    x: x + 0.08, y: y + 0.08, w: w - 0.16, h: 0.12,
    fontFace: FONT, fontSize: 8.5, bold: true, color: C.white,
    margin: 0, fit: "shrink",
  });
}

function bulletList(slide, items, x, y, w, h, size = 15) {
  slide.addText(items.map((text) => ({ text, options: { bullet: { indent: 14 }, hanging: 4 } })), {
    x, y, w, h,
    fontFace: FONT, fontSize: size, color: C.ink,
    paraSpaceAfterPt: 8, fit: "shrink", breakLine: false,
    margin: 0.02, valign: "top",
  });
}

function addTable(slide, rows, x, y, widths, rowH = 0.5, highlightRow = -1) {
  let cy = y;
  rows.forEach((row, ri) => {
    let cx = x;
    row.forEach((cell, ci) => {
      const fill = ri === 0 ? C.light : ri === highlightRow ? C.warn : C.white;
      slide.addShape(pptx.ShapeType.rect, {
        x: cx, y: cy, w: widths[ci], h: rowH,
        fill: { color: fill },
        line: { color: C.grid, width: 0.8 },
      });
      slide.addText(String(cell), {
        x: cx + 0.07, y: cy + 0.08, w: widths[ci] - 0.14, h: rowH - 0.12,
        fontFace: FONT,
        fontSize: ri === 0 ? 10 : 9.6,
        bold: ri === 0 || ri === highlightRow,
        color: ri === 0 ? C.green : C.ink,
        margin: 0,
        fit: "shrink",
        valign: "mid",
      });
      cx += widths[ci];
    });
    cy += rowH;
  });
}

function addMetric(slide, value, label, x, y, w) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.82,
    rectRadius: 0.04,
    fill: { color: C.white },
    line: { color: C.grid, width: 1 },
  });
  slide.addText(value, {
    x: x + 0.12, y: y + 0.12, w: w - 0.24, h: 0.25,
    fontFace: FONT, fontSize: 16, bold: true, color: C.green,
    align: "center", margin: 0, fit: "shrink",
  });
  slide.addText(label, {
    x: x + 0.12, y: y + 0.48, w: w - 0.24, h: 0.18,
    fontFace: FONT, fontSize: 9.2, color: C.muted,
    align: "center", margin: 0, fit: "shrink",
  });
}

function addPipeline(slide, labels, y) {
  const x0 = 0.68;
  const w = 1.55;
  labels.forEach((label, index) => {
    const x = x0 + index * 1.92;
    slide.addShape(pptx.ShapeType.roundRect, {
      x, y, w, h: 0.72,
      rectRadius: 0.05,
      fill: { color: index === 0 ? C.green : C.white },
      line: { color: index === 0 ? C.green : C.grid, width: 1 },
    });
    slide.addText(label, {
      x: x + 0.06, y: y + 0.19, w: w - 0.12, h: 0.25,
      fontFace: FONT, fontSize: 10.5, bold: true,
      color: index === 0 ? C.white : C.ink,
      align: "center", margin: 0, fit: "shrink",
    });
    if (index < labels.length - 1) {
      slide.addShape(pptx.ShapeType.rightArrow, {
        x: x + w + 0.1, y: y + 0.23, w: 0.28, h: 0.24,
        fill: { color: C.green },
        line: { color: C.green },
      });
    }
  });
}

function addServiceBox(slide, title, body, x, y, w, h, primary = false) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.04,
    fill: { color: primary ? C.light : C.white },
    line: { color: primary ? C.green : C.grid, width: 1 },
  });
  slide.addText(title, {
    x: x + 0.1, y: y + 0.12, w: w - 0.2, h: 0.2,
    fontFace: FONT, fontSize: 10.2, bold: true, color: C.green,
    margin: 0, fit: "shrink",
  });
  slide.addText(body, {
    x: x + 0.1, y: y + 0.42, w: w - 0.2, h: h - 0.5,
    fontFace: FONT, fontSize: 8.8, color: C.ink,
    margin: 0, fit: "shrink",
  });
}

function modelRows() {
  const localizedRoles = {
    "tfidf-logreg": "лучшая baseline-модель",
    "embedding-logreg": "семантический baseline",
    "tiny-transformer-classifier": "легкая нейросетевая модель",
  };
  return facts.models.map((model) => [
    model.name,
    model.test_accuracy.toFixed(3),
    model.test_macro_f1.toFixed(3),
    localizedRoles[model.name] ?? model.role,
  ]);
}

function formatNumber(value) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

let slide;

slide = pptx.addSlide();
slide.background = { color: C.bg };
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.72, fill: { color: C.green }, line: { color: C.green } });
slide.addText(UNIVERSITY, {
  x: 0.75, y: 0.24, w: 11.8, h: 0.18,
  fontFace: FONT, fontSize: 10.5, bold: true, color: C.white,
  align: "center", margin: 0, fit: "shrink",
});
slide.addText("КУРСОВАЯ РАБОТА", {
  x: 0.75, y: 1.12, w: 11.8, h: 0.26,
  fontFace: FONT, fontSize: 14, bold: true, color: C.green,
  align: "center", margin: 0,
});
slide.addText(facts.coursework.topic, {
  x: 1.1, y: 1.78, w: 11.1, h: 1.3,
  fontFace: FONT, fontSize: 25, bold: true, color: C.ink,
  align: "center", margin: 0, fit: "shrink",
});
slide.addText(`Выполнил: ${STUDENT}\nГруппа: ${GROUP}\nРуководитель: ${facts.student.supervisor}`, {
  x: 6.55, y: 4.05, w: 5.65, h: 0.9,
  fontFace: FONT, fontSize: 12.5, color: C.ink,
  margin: 0, fit: "shrink",
});
slide.addShape(pptx.ShapeType.line, { x: 1.1, y: 5.65, w: 11.1, h: 0, line: { color: C.grid, width: 1 } });
slide.addText(`${facts.student.city}, ${facts.student.year}`, {
  x: 0.75, y: 6.22, w: 11.8, h: 0.22,
  fontFace: FONT, fontSize: 12, color: C.muted,
  align: "center", margin: 0,
});
addFooter(slide, 1);

slide = pptx.addSlide();
addTitle(slide, "Актуальность", "Экономические новости требуют быстрого поиска, фильтрации и интерпретации", 2);
sectionLabel(slide, "Введение: актуальность", 0.75, 1.46, 2.45);
bulletList(slide, [
  "Поток экономических новостей слишком велик для ручного анализа.",
  "Одно событие может по-разному влиять на рынок, компанию или сектор.",
  "Пользователю нужен ответ на естественном языке, но с проверяемыми источниками.",
  "Система объединяет retrieval, ML-оценку влияния и аналитический вывод.",
], 0.8, 1.98, 6.0, 2.55, 16);
addMetric(slide, "50 000", "новостей FNSPID", 7.25, 1.95, 1.55);
addMetric(slide, "3", "модели анализа", 9.05, 1.95, 1.55);
addMetric(slide, formatNumber(facts.forecast.documents), "документов в прогнозе", 10.85, 1.95, 1.8);
addPipeline(slide, ["новости", "вопрос", "поиск", "ML-анализ", "ответ", "прогноз"], 5.15);

slide = pptx.addSlide();
addTitle(slide, "Цель и задачи", "Цель: разработать диалоговую систему для анализа экономических новостей", 3);
sectionLabel(slide, "Введение: цель и задачи", 0.78, 1.42, 2.8);
slide.addText("Цель работы", {
  x: 0.82, y: 1.85, w: 3.0, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
slide.addText("Создать систему, которая принимает вопрос пользователя, находит релевантные экономические новости, оценивает их влияние и формирует ответ с источниками.", {
  x: 0.82, y: 2.22, w: 5.4, h: 1.05,
  fontFace: FONT, fontSize: 15, color: C.ink, margin: 0, fit: "shrink",
});
slide.addText("Задачи", {
  x: 6.75, y: 1.85, w: 3.0, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Подготовить датасет FNSPID и постановку ML-задачи.",
  "Сравнить три модели классификации влияния.",
  "Реализовать retrieval и RAG-ответ по источникам.",
  "Подключить внешнюю языковую модель для аналитического вывода.",
  "Собрать веб-интерфейс и микросервисную backend-архитектуру.",
], 6.75, 2.22, 5.5, 2.95, 14);

slide = pptx.addSlide();
addTitle(slide, "Данные и постановка задачи", "FNSPID используется как корпус экономических новостей для обучения и анализа", 4);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
addMetric(slide, formatNumber(facts.dataset.rows), "строк в датасете", 0.9, 1.92, 1.7);
addMetric(slide, "3", "класса влияния", 2.85, 1.92, 1.45);
addMetric(slide, "train / val / test", "разделение выборки", 4.55, 1.92, 1.8);
addTable(slide, [
  ["Элемент", "Описание"],
  ["Объект анализа", "экономическая новость"],
  ["Вход модели", "заголовок и полный текст новости"],
  ["Целевая переменная", "positive / neutral / negative"],
  ["Проблема данных", "шумная разметка и дисбаланс классов"],
  ["Ключевая метрика", "macro F1, так как важны все классы"],
], 0.9, 3.15, [3.1, 8.0], 0.48);
slide.addText("Классификация используется не изолированно: ее результат входит в RAG-ответ и тематический прогноз.", {
  x: 0.9, y: 6.2, w: 10.9, h: 0.35,
  fontFace: FONT, fontSize: 13.2, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "ML-модели и метрики", "Сравниваются простая, семантическая и легкая нейросетевая модель", 5);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
addTable(slide, [
  ["Модель", "Идея", "Зачем нужна"],
  ["tfidf-logreg", "TF-IDF + Logistic Regression", "быстрый и объяснимый baseline"],
  ["embedding-logreg", "embeddings + Logistic Regression", "проверка семантических признаков"],
  ["tiny-transformer-classifier", "легкий transformer", "нейросетевой вариант с малым потреблением ресурсов"],
], 0.82, 1.95, [2.75, 4.0, 5.0], 0.65);
bulletList(slide, [
  "Accuracy показывает общую долю верных классификаций.",
  "Macro F1 показывает качество по каждому классу и важен при дисбалансе.",
  "Inference time нужен, чтобы оценить применимость модели в интерактивной системе.",
], 0.95, 4.9, 10.8, 1.2, 14);

slide = pptx.addSlide();
addTitle(slide, "Результаты моделей", "Лучшее качество показала TF-IDF + Logistic Regression", 6);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
addTable(slide, [
  ["Модель", "Test accuracy", "Test macro F1", "Роль"],
  ...modelRows(),
], 0.78, 1.9, [3.0, 2.0, 2.0, 4.8], 0.58, 1);
bulletList(slide, [
  "TF-IDF + Logistic Regression стала наиболее устойчивой baseline-моделью.",
  "Качество ограничено шумом разметки, дисбалансом классов и сложностью экономического контекста.",
  "Выбранный baseline рационален для текущего RAG-сценария: он быстрый, объяснимый и воспроизводимый.",
], 0.95, 4.75, 10.8, 1.25, 14);
slide.addText(`Лучший Test macro F1: ${facts.models[0].test_macro_f1.toFixed(3)} · тематических групп в прогнозе: ${formatNumber(facts.forecast.topics)}`, {
  x: 0.95, y: 6.18, w: 10.8, h: 0.28,
  fontFace: FONT, fontSize: 12.5, bold: true, color: C.blue,
  margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "ML/RAG-пайплайн", "Ответ формируется по найденным новостям, а не как абстрактная генерация", 7);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
addPipeline(slide, ["вопрос", "поиск", "источники", "ML-оценка", "LLM/API", "ответ"], 2.0);
addTable(slide, [
  ["Шаг", "Результат"],
  ["Поиск", "top-k релевантных новостей из Qdrant"],
  ["Анализ", "impact, confidence и объяснение для источников"],
  ["RAG", "ответ строится по найденному контексту"],
  ["Прогноз", "языковая модель формирует сценарный вывод по фактам"],
], 0.9, 3.25, [2.55, 8.4], 0.52);

slide = pptx.addSlide();
addTitle(slide, "Микросервисная архитектура", "Сервисы разделяют UI, поиск, анализ, диалог и работу с данными", 8);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
slide.addImage({ path: path.join(assetsDir, "architecture-diagram.png"), x: 0.75, y: 1.85, w: 11.85, h: 4.95 });
slide.addText("Архитектура оставляет ML-часть наблюдаемой: можно отдельно проверить данные, retrieval, классификацию и итоговую генерацию.", {
  x: 0.95, y: 6.28, w: 10.9, h: 0.28,
  fontFace: FONT, fontSize: 12.5, bold: true, color: C.blue,
  margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Страница чата", "Пользователь получает ответ, источники и ход обработки запроса", 9);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
slide.addImage({ path: path.join(assetsDir, "chat-page.png"), x: 0.72, y: 1.85, w: 7.2, h: 4.85, sizingCrop: true });
bulletList(slide, [
  "Вопрос задается на естественном языке.",
  "Ответ строится по найденным новостям.",
  "Источники показываются рядом с оценкой релевантности и ML-сигналом.",
  "Timeline делает обработку запроса прозрачной.",
], 8.35, 2.0, 3.9, 3.0, 13.6);

slide = pptx.addSlide();
addTitle(slide, "Страница ML-отчета", "Отчет показывает качество моделей и объясняет выбор baseline", 10);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
slide.addImage({ path: path.join(assetsDir, "ml-report-page.png"), x: 0.72, y: 1.85, w: 7.2, h: 4.85, sizingCrop: true });
bulletList(slide, [
  "Сравниваются три модели на одном test split.",
  "Отображаются accuracy, macro F1 и скорость инференса.",
  "Матрица ошибок помогает понять слабые классы.",
  "Top-признаки показывают интерпретируемость TF-IDF baseline.",
], 8.35, 2.0, 3.9, 3.0, 13.2);

slide = pptx.addSlide();
addTitle(slide, "Страница прогноза", "Система объединяет новости по темам и формирует сценарный вывод", 11);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
slide.addImage({ path: path.join(assetsDir, "topic-forecast-page.png"), x: 0.72, y: 1.85, w: 7.2, h: 4.85, sizingCrop: true });
bulletList(slide, [
  `Прогноз строится по ${formatNumber(facts.forecast.documents)} документам.`,
  `Найдено ${formatNumber(facts.forecast.topics)} тематических групп.`,
  "Для группы учитываются сигналы нескольких моделей.",
  "Подключаемая языковая модель формулирует прогноз по фактам из новостей.",
], 8.35, 2.0, 3.9, 3.0, 13.2);

slide = pptx.addSlide();
addTitle(slide, "Инженерная реализация", "Backend поддерживает ML-сценарий, не подменяя исследовательскую часть", 12);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
addServiceBox(slide, "FastAPI + asyncio", "асинхронные API и потоковые ответы через SSE", 0.85, 1.92, 2.55, 1.0, true);
addServiceBox(slide, "DDD и слои", "domain, application, infrastructure, presentation, main", 3.7, 1.92, 2.55, 1.0);
addServiceBox(slide, "Protocol + Dishka", "интерфейсы и сборка зависимостей без жесткой связности", 6.55, 1.92, 2.55, 1.0);
addServiceBox(slide, "Qdrant", "векторный индекс для retrieval-поиска", 9.4, 1.92, 2.55, 1.0);
addServiceBox(slide, "Redis + Taskiq", "фоновые задачи индексации и событийная обработка", 2.1, 3.55, 2.8, 1.0);
addServiceBox(slide, "MLflow", "метрики, эксперименты и артефакты моделей", 5.25, 3.55, 2.8, 1.0);
addServiceBox(slide, "React UI", "чат, данные, ML-отчет и прогноз", 8.4, 3.55, 2.8, 1.0, true);
slide.addText("Главная идея: backend организует надежный путь данных от корпуса к ответу, а ML-компоненты остаются проверяемыми через отчет и метрики.", {
  x: 0.95, y: 5.55, w: 10.9, h: 0.48,
  fontFace: FONT, fontSize: 13, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Ограничения и улучшения", "Качество моделей можно повышать за счет данных, параметров и более сильных признаков", 13);
sectionLabel(slide, "Методы и результаты", 0.78, 1.42, 2.35);
slide.addText("Текущие ограничения", {
  x: 0.9, y: 1.85, w: 3.5, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Разметка экономического влияния может быть шумной.",
  "Классы распределены неравномерно.",
  "Маленький transformer ограничен размером и режимом обучения.",
  "Retrieval-качество нужно оценивать отдельно от классификации.",
], 0.9, 2.25, 5.3, 2.2, 14);
slide.addText("Что улучшать", {
  x: 6.7, y: 1.85, w: 3.5, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Очистка и уточнение спорной разметки.",
  "Балансировка классов и подбор гиперпараметров.",
  "Более сильные embeddings и transformer-модель.",
  "Добавление признаков: сектор, компания, дата и источник.",
], 6.7, 2.25, 5.3, 2.2, 14);

slide = pptx.addSlide();
addTitle(slide, "Заключение", "Реализована диалоговая ML-система для анализа экономических новостей", 14);
sectionLabel(slide, "Заключение", 0.78, 1.42, 1.45);
slide.addText("Получено", {
  x: 0.9, y: 1.85, w: 3.0, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Подготовлен датасет FNSPID на 50 000 новостей.",
  "Сравнены три модели классификации влияния.",
  "Реализованы retrieval, RAG-ответ, ML-отчет и прогноз.",
  "Собрана микросервисная система с React UI.",
], 0.9, 2.25, 5.3, 2.2, 14.2);
slide.addText("Вывод", {
  x: 6.7, y: 1.85, w: 3.0, h: 0.25,
  fontFace: FONT, fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Цель работы достигнута.",
  "Лучший baseline: TF-IDF + Logistic Regression.",
  "Система показывает полный путь: данные, модели, источники, ответ и прогноз.",
  "Проект соответствует теме курсовой работы.",
], 6.7, 2.25, 5.3, 2.2, 14.2);
slide.addText("Итог: проект объединяет диалоговый интерфейс, ML-анализ экономических новостей и подключаемую языковую модель.", {
  x: 0.9, y: 5.55, w: 10.9, h: 0.45,
  fontFace: FONT, fontSize: 13.5, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Источники", "Датасет, статьи и документация используемых технологий", 15);
sectionLabel(slide, "Список источников", 0.78, 1.42, 1.9);
bulletList(slide, facts.sources, 0.82, 1.88, 11.1, 4.8, 10.2);

fs.mkdirSync(finalDir, { recursive: true });
await pptx.writeFile({ fileName: pptxPath });
console.log(pptxPath);
