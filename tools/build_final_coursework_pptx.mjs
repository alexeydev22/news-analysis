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
const TOTAL_SLIDES = 11;

const pptx = new pptxgen();
pptx.author = STUDENT;
pptx.subject = "Курсовая работа";
pptx.title = facts.coursework.topic;
pptx.company = UNIVERSITY;
pptx.lang = "ru-RU";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
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
    fontFace: "Arial", fontSize: 8.5, color: C.muted, align: "right",
    margin: 0,
  });
}

function addTitle(slide, text, subtitle, n) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.green }, line: { color: C.green } });
  slide.addText(text, {
    x: 0.65, y: 0.42, w: 11.6, h: 0.55,
    fontFace: "Arial", fontSize: 24, bold: true, color: C.ink,
    margin: 0, fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.67, y: 1.05, w: 11.1, h: 0.35,
      fontFace: "Arial", fontSize: 12, color: C.muted,
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
    fontFace: "Arial", fontSize: 8.5, bold: true, color: C.white,
    margin: 0, fit: "shrink",
  });
}

function bulletList(slide, items, x, y, w, h, size = 15) {
  slide.addText(items.map((text) => ({ text, options: { bullet: { indent: 14 }, hanging: 4 } })), {
    x, y, w, h,
    fontFace: "Arial", fontSize: size, color: C.ink,
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
        fontFace: "Arial",
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
    fontFace: "Arial", fontSize: 16, bold: true, color: C.green,
    align: "center", margin: 0, fit: "shrink",
  });
  slide.addText(label, {
    x: x + 0.12, y: y + 0.48, w: w - 0.24, h: 0.18,
    fontFace: "Arial", fontSize: 9.2, color: C.muted,
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
      fontFace: "Arial", fontSize: 10.5, bold: true,
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
    fontFace: "Arial", fontSize: 10.2, bold: true, color: C.green,
    margin: 0, fit: "shrink",
  });
  slide.addText(body, {
    x: x + 0.1, y: y + 0.42, w: w - 0.2, h: h - 0.5,
    fontFace: "Arial", fontSize: 8.8, color: C.ink,
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
  fontFace: "Arial", fontSize: 10.5, bold: true, color: C.white,
  align: "center", margin: 0, fit: "shrink",
});
slide.addText("КУРСОВАЯ РАБОТА", {
  x: 0.75, y: 1.25, w: 11.8, h: 0.26,
  fontFace: "Arial", fontSize: 14, bold: true, color: C.green,
  align: "center", margin: 0,
});
slide.addText(facts.coursework.topic, {
  x: 1.1, y: 1.85, w: 11.1, h: 1.28,
  fontFace: "Arial", fontSize: 25, bold: true, color: C.ink,
  align: "center", margin: 0, fit: "shrink",
});
slide.addText(`Выполнил: ${STUDENT}\nГруппа: ${GROUP}\nРуководитель: ____________________`, {
  x: 7.1, y: 4.18, w: 4.95, h: 0.8,
  fontFace: "Arial", fontSize: 13, color: C.ink,
  margin: 0, fit: "shrink",
});
slide.addShape(pptx.ShapeType.line, { x: 1.1, y: 5.65, w: 11.1, h: 0, line: { color: C.grid, width: 1 } });
slide.addText(`${facts.student.city}, ${facts.student.year}`, {
  x: 0.75, y: 6.22, w: 11.8, h: 0.22,
  fontFace: "Arial", fontSize: 12, color: C.muted,
  align: "center", margin: 0,
});
addFooter(slide, 1);

slide = pptx.addSlide();
addTitle(slide, "Актуальность", "Экономические новости требуют быстрого поиска, фильтрации и интерпретации", 2);
sectionLabel(slide, "Критерий: введение / актуальность", 0.75, 1.46, 3.1);
bulletList(slide, [
  "Поток экономических новостей слишком велик для ручного анализа.",
  "Одно событие может иметь разное влияние на рынок, компанию или сектор.",
  "Пользователю нужен ответ на естественном языке, но с опорой на источники.",
  "Диалоговая система объединяет поиск, ML-оценку влияния и краткий аналитический вывод.",
], 0.8, 1.98, 6.0, 2.55, 16);
addMetric(slide, "50 000", "новостей FNSPID", 7.25, 1.95, 1.55);
addMetric(slide, "3", "модели анализа", 9.05, 1.95, 1.55);
addMetric(slide, formatNumber(facts.forecast.documents), "документов в прогнозе", 10.85, 1.95, 1.8);
addPipeline(slide, ["новости", "вопрос", "поиск", "ML-анализ", "ответ", "прогноз"], 5.15);

slide = pptx.addSlide();
addTitle(slide, "Цель и задачи", "Цель: разработать диалоговую систему для анализа экономических новостей", 3);
sectionLabel(slide, "Критерий: введение / цель и задачи", 0.78, 1.42, 3.15);
slide.addText("Цель работы", {
  x: 0.82, y: 1.85, w: 3.0, h: 0.25,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
slide.addText("Создать систему, которая принимает вопрос пользователя, находит релевантные экономические новости, оценивает их влияние и формирует ответ с источниками.", {
  x: 0.82, y: 2.22, w: 5.4, h: 1.0,
  fontFace: "Arial", fontSize: 15, color: C.ink, margin: 0, fit: "shrink",
});
slide.addText("Задачи", {
  x: 6.75, y: 1.85, w: 3.0, h: 0.25,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Подготовить датасет FNSPID и постановку ML-задачи.",
  "Сравнить три модели классификации влияния.",
  "Реализовать retrieval и RAG-ответ по источникам.",
  "Подключить внешний LLM API для аналитического прогноза.",
  "Собрать веб-интерфейс и микросервисную backend-архитектуру.",
], 6.75, 2.22, 5.5, 2.95, 14);

slide = pptx.addSlide();
addTitle(slide, "Данные и постановка задачи", "FNSPID используется как корпус экономических новостей для обучения и анализа", 4);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
addMetric(slide, String(facts.dataset.rows), "строк в датасете", 0.9, 1.92, 1.7);
addMetric(slide, "3", "класса влияния", 2.85, 1.92, 1.45);
addMetric(slide, "train/val/test", "разделение выборки", 4.55, 1.92, 1.8);
addTable(slide, [
  ["Элемент", "Описание"],
  ["Объект анализа", "экономическая новость"],
  ["Вход модели", "заголовок и текст новости"],
  ["Целевая переменная", "positive / neutral / negative"],
  ["Проблема данных", "шумная разметка и дисбаланс классов"],
  ["Ключевая метрика", "macro F1, так как важны все классы"],
], 0.9, 3.15, [3.1, 8.0], 0.48);
slide.addText("Задача классификации используется не изолированно: ее результат входит в RAG-сценарий ответа и тематический прогноз.", {
  x: 0.9, y: 6.2, w: 10.9, h: 0.35,
  fontFace: "Arial", fontSize: 13.2, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Методы анализа", "Сравниваются простая, семантическая и легкая нейросетевая модель", 5);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
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
addTitle(slide, "ML/RAG-пайплайн", "Ответ формируется по найденным новостям, а не как абстрактная генерация", 6);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
addPipeline(slide, ["вопрос", "поиск", "источники", "ML-оценка", "LLM/API", "ответ"], 2.0);
addTable(slide, [
  ["Шаг", "Результат"],
  ["Поиск", "top-k релевантных новостей из Qdrant"],
  ["Анализ", "impact, confidence и объяснение для источников"],
  ["RAG", "ответ строится по найденному контексту"],
  ["Прогноз", "языковая модель через API формирует сценарный вывод по фактам"],
], 0.9, 3.25, [2.55, 8.4], 0.52);

slide = pptx.addSlide();
addTitle(slide, "Архитектура приложения", "Микросервисы разделяют UI, поиск, анализ, диалог и работу с данными", 7);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
addServiceBox(slide, "React UI", "Чат, ML-отчет, прогноз, загрузка данных", 0.85, 1.92, 2.0, 0.95, true);
addServiceBox(slide, "API Gateway", "Единая точка входа и SSE-сценарий", 3.25, 1.92, 2.0, 0.95, true);
addServiceBox(slide, "analysis-service", "Классификация влияния и ML-отчет", 5.65, 1.92, 2.0, 0.95);
addServiceBox(slide, "retrieval-service", "Векторный поиск и Qdrant", 8.05, 1.92, 2.0, 0.95);
addServiceBox(slide, "dialog-service", "Ответ и внешний LLM API", 10.45, 1.92, 2.0, 0.95);
addServiceBox(slide, "news-service", "Загрузка CSV и активный датасет", 1.95, 3.55, 2.25, 0.95);
addServiceBox(slide, "Redis + Taskiq", "Фоновые задачи и события", 4.75, 3.55, 2.25, 0.95);
addServiceBox(slide, "Qdrant", "Векторное хранилище документов", 7.55, 3.55, 2.25, 0.95);
addServiceBox(slide, "MLflow", "Учет экспериментов и артефактов", 10.35, 3.55, 2.25, 0.95);
slide.addText("Backend построен слоисто: domain, application, infrastructure, presentation, main. Интерфейсы описаны через Protocol, зависимости собираются через Dishka.", {
  x: 0.9, y: 5.55, w: 11.35, h: 0.55,
  fontFace: "Arial", fontSize: 13.2, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Результаты моделей", "Лучшее качество показала TF-IDF + Logistic Regression", 8);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
addTable(slide, [
  ["Модель", "Test accuracy", "Test macro F1", "Роль"],
  ...modelRows(),
], 0.78, 1.9, [3.0, 2.0, 2.0, 4.8], 0.58, 1);
bulletList(slide, [
  "TF-IDF + Logistic Regression стала лучшей baseline-моделью на текущей разметке.",
  "Качество ограничено шумом данных и дисбалансом классов.",
  "Модель пригодна как базовый классификатор для RAG-системы и дальнейших экспериментов.",
], 0.95, 4.75, 10.8, 1.25, 14);
slide.addText(`Лучший Test macro F1: ${facts.models[0].test_macro_f1.toFixed(3)} · тематических групп в прогнозе: ${formatNumber(facts.forecast.topics)}`, {
  x: 0.95, y: 6.18, w: 10.8, h: 0.28,
  fontFace: "Arial", fontSize: 12.5, bold: true, color: C.blue,
  margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Работа приложения", "Три ключевые страницы: чат, ML-отчет и прогноз", 9);
sectionLabel(slide, "Критерий: методы и результаты", 0.78, 1.42, 2.65);
const screenshots = [
  ["Чат", "chat-page.png"],
  ["ML-отчет", "ml-report-page.png"],
  ["Прогноз", "topic-forecast-page.png"],
];
screenshots.forEach(([label, file], index) => {
  const x = 0.58 + index * 4.2;
  slide.addText(label, {
    x, y: 1.82, w: 3.75, h: 0.22,
    fontFace: "Arial", fontSize: 12.5, bold: true, color: C.green,
    align: "center", margin: 0,
  });
  slide.addImage({ path: path.join(assetsDir, file), x, y: 2.12, w: 3.75, h: 3.1, sizingCrop: true });
});
bulletList(slide, [
  "Чат показывает ответ, источники и ход обработки.",
  "ML-отчет показывает метрики трех моделей на 50 000 строк.",
  `Прогноз показывает тематические группы и сценарные выводы по ${formatNumber(facts.forecast.documents)} документам.`,
], 0.82, 5.65, 11.3, 0.95, 12.2);

slide = pptx.addSlide();
addTitle(slide, "Заключение", "Реализована диалоговая ML-система для анализа экономических новостей", 10);
sectionLabel(slide, "Критерий: заключение", 0.78, 1.42, 1.85);
slide.addText("Получено", {
  x: 0.9, y: 1.85, w: 3.0, h: 0.25,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Подготовлен датасет FNSPID на 50 000 новостей.",
  "Сравнены три модели классификации влияния.",
  "Реализованы retrieval, RAG-ответ, ML-отчет и прогноз.",
  "Собрана микросервисная система с React UI.",
], 0.9, 2.25, 5.3, 2.2, 14.2);
slide.addText("Дальнейшее улучшение", {
  x: 6.7, y: 1.85, w: 3.8, h: 0.25,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Уточнение и очистка разметки.",
  "Балансировка классов и подбор гиперпараметров.",
  "Дообучение более сильной transformer-модели.",
  "Оценка качества тематического прогнозирования.",
], 6.7, 2.25, 5.3, 2.2, 14.2);
slide.addText("Итог: проект соответствует теме, так как объединяет диалоговый интерфейс, ML-анализ экономических новостей и подключаемую языковую модель.", {
  x: 0.9, y: 5.55, w: 10.9, h: 0.45,
  fontFace: "Arial", fontSize: 13.5, bold: true, color: C.blue, margin: 0, fit: "shrink",
});

slide = pptx.addSlide();
addTitle(slide, "Источники", "Методические материалы, датасет и документация используемых технологий", 11);
sectionLabel(slide, "Критерий: список источников", 0.78, 1.42, 2.25);
bulletList(slide, facts.sources, 0.82, 1.95, 11.1, 4.6, 15);

fs.mkdirSync(finalDir, { recursive: true });
await pptx.writeFile({ fileName: pptxPath });
console.log(pptxPath);
