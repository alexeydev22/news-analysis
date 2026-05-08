import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");

const root = process.cwd();
const finalDir = path.join(root, "docs", "final");
const assetsDir = path.join(finalDir, "assets");
const pptxPath = path.join(finalDir, "coursework-defense-presentation.pptx");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "news-analysis";
pptx.subject = "Курсовая работа";
pptx.title = "Диалоговая система анализа экономических новостей";
pptx.company = "news-analysis";
pptx.lang = "ru-RU";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  lang: "ru-RU",
};
pptx.defineLayout({ name: "COURSE", width: 13.333, height: 7.5 });
pptx.layout = "COURSE";

const C = {
  bg: "F7FAF8",
  ink: "17211D",
  muted: "60706A",
  green: "0F5132",
  light: "EAF4EF",
  grid: "C8D8D1",
  blue: "1F4D78",
  white: "FFFFFF",
};

function addFooter(slide, n) {
  slide.addText(`news-analysis · ${n}/12`, {
    x: 0.55, y: 7.08, w: 12.2, h: 0.22,
    fontFace: "Arial", fontSize: 8.5, color: C.muted, align: "right",
  });
}

function title(slide, text, subtitle, n) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.green }, line: { color: C.green } });
  slide.addText(text, {
    x: 0.65, y: 0.45, w: 10.8, h: 0.85,
    fontFace: "Arial", fontSize: 27, bold: true, color: C.ink,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.67, y: 1.24, w: 10.8, h: 0.35,
      fontFace: "Arial", fontSize: 12.5, color: C.muted,
      margin: 0,
    });
  }
  addFooter(slide, n);
}

function bulletList(slide, items, x, y, w, h, size = 17) {
  slide.addText(items.map((t) => ({ text: t, options: { bullet: { indent: 14 }, hanging: 4 } })), {
    x, y, w, h,
    fontFace: "Arial",
    fontSize: size,
    color: C.ink,
    breakLine: false,
    valign: "top",
    fit: "shrink",
    paraSpaceAfterPt: 8,
    margin: 0.02,
  });
}

function chip(slide, text, x, y, w) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.44,
    rectRadius: 0.05,
    fill: { color: C.light },
    line: { color: C.grid, width: 1 },
  });
  slide.addText(text, {
    x: x + 0.12, y: y + 0.11, w: w - 0.24, h: 0.18,
    fontFace: "Arial", fontSize: 10.5, bold: true, color: C.green,
    margin: 0, fit: "shrink",
  });
}

function addTableLike(slide, rows, x, y, widths, rowH = 0.52) {
  let cy = y;
  rows.forEach((row, ri) => {
    let cx = x;
    row.forEach((cell, ci) => {
      const fill = ri === 0 ? C.light : C.white;
      slide.addShape(pptx.ShapeType.rect, {
        x: cx, y: cy, w: widths[ci], h: rowH,
        fill: { color: fill },
        line: { color: C.grid, width: 0.8 },
      });
      slide.addText(cell, {
        x: cx + 0.08, y: cy + 0.1, w: widths[ci] - 0.16, h: rowH - 0.14,
        fontFace: "Arial",
        fontSize: ri === 0 ? 10.5 : 10,
        bold: ri === 0,
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

function addPipeline(slide, labels, y) {
  const x0 = 0.75;
  const w = 1.75;
  labels.forEach((label, i) => {
    const x = x0 + i * 2.05;
    slide.addShape(pptx.ShapeType.roundRect, {
      x, y, w, h: 0.78,
      rectRadius: 0.06,
      fill: { color: i === 0 ? C.green : C.white },
      line: { color: i === 0 ? C.green : C.grid, width: 1.1 },
    });
    slide.addText(label, {
      x: x + 0.08, y: y + 0.2, w: w - 0.16, h: 0.3,
      fontFace: "Arial", fontSize: 11.5, bold: true,
      color: i === 0 ? C.white : C.ink,
      align: "center", margin: 0, fit: "shrink",
    });
    if (i < labels.length - 1) {
      slide.addShape(pptx.ShapeType.rightArrow, {
        x: x + w + 0.12, y: y + 0.24, w: 0.32, h: 0.28,
        fill: { color: C.green },
        line: { color: C.green },
      });
    }
  });
}

let slide;

slide = pptx.addSlide();
slide.background = { color: C.bg };
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 1.0, fill: { color: C.green }, line: { color: C.green } });
slide.addText("Разработка автоматической диалоговой системы\nна основе языковой модели для анализа\nэкономических новостей", {
  x: 0.75, y: 1.75, w: 10.9, h: 1.75,
  fontFace: "Arial", fontSize: 30, bold: true, color: C.ink,
  margin: 0, fit: "shrink",
});
slide.addText("Курсовая работа · ФИО, группа, руководитель, 2026", {
  x: 0.78, y: 3.72, w: 9.8, h: 0.3,
  fontFace: "Arial", fontSize: 14, color: C.muted,
  margin: 0,
});
chip(slide, "локальный RAG pipeline", 0.8, 4.55, 2.2);
chip(slide, "микросервисы", 3.25, 4.55, 1.75);
chip(slide, "FastAPI + React", 5.25, 4.55, 1.9);
chip(slide, "Qdrant + Redis", 7.4, 4.55, 1.9);
addFooter(slide, 1);
slide.addNotes("Тема работы и общий результат: локальная система, которая отвечает на вопросы по экономическим новостям и показывает источники.");

slide = pptx.addSlide();
title(slide, "Актуальность", "Пользователю нужен быстрый ответ по множеству экономических сообщений", 2);
bulletList(slide, [
  "Экономические новости быстро меняют ожидания рынка.",
  "Ручной анализ множества источников занимает время.",
  "Диалоговый формат снижает порог входа.",
  "Ответ должен опираться на найденные источники, а не только на общие знания модели.",
], 0.8, 2.0, 5.5, 2.8, 18);
addPipeline(slide, ["много новостей", "вопрос", "поиск", "анализ", "ответ"], 5.25);

slide = pptx.addSlide();
title(slide, "Цель и задачи", "Цель: найти новости, оценить влияние и сформировать ответ", 3);
bulletList(slide, [
  "Спроектировать микросервисную архитектуру.",
  "Реализовать загрузку и индексацию новостей.",
  "Реализовать векторный поиск релевантных источников.",
  "Реализовать анализ влияния новости.",
  "Реализовать генерацию ответа с поддержкой языковой модели.",
  "Подготовить web UI и demo-сценарий.",
], 0.8, 1.9, 10.8, 4.1, 17);

slide = pptx.addSlide();
title(slide, "Общая архитектура", "Каждый сервис отвечает за отдельную часть диалогового сценария", 4);
slide.addImage({ path: path.join(assetsDir, "architecture-diagram.png"), x: 0.55, y: 1.55, w: 12.1, h: 5.2 });

slide = pptx.addSlide();
title(slide, "Pipeline обработки вопроса", "SSE показывает пользователю ход выполнения", 5);
addPipeline(slide, ["вопрос", "retrieval", "analysis", "dialog", "источники", "ответ"], 2.15);
bulletList(slide, [
  "Gateway получает вопрос и запускает поток событий.",
  "Retrieval-service ищет релевантные новости в Qdrant.",
  "Analysis-service оценивает влияние каждой новости.",
  "Dialog-service собирает итоговый ответ.",
], 1.0, 4.0, 10.2, 1.8, 17);

slide = pptx.addSlide();
title(slide, "Методы и технологии", "Стек современный, но локальный и без лишней инфраструктуры", 6);
addTableLike(slide, [
  ["Часть", "Выбор"],
  ["Backend", "FastAPI, asyncio, Granian"],
  ["Архитектура", "DDD, слои, Protocol, Dishka"],
  ["Фоновые задачи", "Taskiq + Redis"],
  ["События", "FastStream + Redis"],
  ["Векторный поиск", "Qdrant"],
  ["ML tracking", "MLflow"],
  ["Frontend", "React"],
], 0.9, 1.55, [3.1, 7.7], 0.55);

slide = pptx.addSlide();
title(slide, "Анализ и генерация", "Воспроизводимый demo-режим плюс возможность подключения LLM", 7);
bulletList(slide, [
  "tfidf-logreg: стабильный режим анализа влияния для защиты.",
  "embedding-logreg и tiny-transformer-classifier: предусмотрены контрактами.",
  "template generator: локальный fallback без зависимости от модели.",
  "LLM-режим: OpenAI-compatible сервер, например llama.cpp.",
  "Легкая модель: Qwen3-0.6B-Instruct-GGUF.",
], 0.8, 1.8, 10.6, 3.6, 17);

slide = pptx.addSlide();
title(slide, "Интерфейс приложения", "Пользователь видит ответ, источники и timeline обработки", 8);
slide.addImage({ path: path.join(assetsDir, "ui-demo-screenshot.png"), x: 0.55, y: 1.45, w: 12.2, h: 5.3 });

slide = pptx.addSlide();
title(slide, "Результаты проверки", "Demo smoke подтверждает end-to-end сценарий", 9);
addTableLike(slide, [
  ["Проверка", "Результат"],
  ["api-gateway health", "ok"],
  ["news-service health", "ok"],
  ["CSV preview", "5 документов"],
  ["index CSV", "5 документов"],
  ["Taskiq job", "queued"],
  ["chat SSE", "8 событий"],
  ["frontend HTML", "ok"],
], 0.9, 1.5, [4.0, 5.5], 0.55);
slide.addText("Команды: just demo-up → just demo-smoke → just demo-down", {
  x: 0.9, y: 6.25, w: 9.8, h: 0.35,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});

slide = pptx.addSlide();
title(slide, "Соответствие теме", "Все ключевые части темы закрыты реализованным сценарием", 10);
addTableLike(slide, [
  ["Требование темы", "Что реализовано"],
  ["Автоматическая диалоговая система", "Web UI + chat SSE endpoint"],
  ["Языковая модель", "LLM-адаптер в dialog-service"],
  ["Анализ экономических новостей", "analysis-service + demo dataset"],
  ["Работа с источниками", "retrieval pipeline + Qdrant"],
  ["Воспроизводимый результат", "Docker Compose + smoke-сценарий"],
], 0.8, 1.65, [4.7, 6.5], 0.68);

slide = pptx.addSlide();
title(slide, "Заключение", "Получился локальный end-to-end стенд для защиты", 11);
bulletList(slide, [
  "Разработана микросервисная диалоговая система.",
  "Реализованы загрузка, поиск, анализ и генерация ответа.",
  "Подготовлен React UI.",
  "Система запускается локально через Docker Compose.",
  "Подготовлен воспроизводимый demo-сценарий.",
], 0.8, 1.8, 6.3, 3.2, 18);
bulletList(slide, [
  "Развитие: реальные новостные API.",
  "История диалогов в PostgreSQL.",
  "Обученные артефакты дополнительных моделей.",
  "Сравнение качества template и LLM-режимов.",
], 7.2, 1.8, 5.1, 3.2, 16);

slide = pptx.addSlide();
title(slide, "Источники", "Документация технологий и базовые материалы по NLP/архитектуре", 12);
bulletList(slide, [
  "FastAPI, Granian, Pydantic, Dishka.",
  "Taskiq, FastStream, Redis.",
  "Qdrant, MLflow, Docker Compose.",
  "React.",
  "Domain-Driven Design.",
  "Retrieval-Augmented Generation.",
  "Attention Is All You Need.",
], 0.8, 1.8, 10.2, 4.0, 17);

fs.mkdirSync(finalDir, { recursive: true });
await pptx.writeFile({ fileName: pptxPath });
console.log(pptxPath);
