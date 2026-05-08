import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");

const root = process.cwd();
const finalDir = path.join(root, "docs", "final");
const assetsDir = path.join(finalDir, "assets");
const pptxPath = path.join(finalDir, "coursework-defense-presentation.pptx");
const UNIVERSITY = "Финансовый университет при Правительстве РФ";
const STUDENT = "Прудиев Алексей Сергеевич";
const GROUP = "ПМ23-4";

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "news-analysis";
pptx.subject = "Курсовая работа";
pptx.title = "Диалоговая система анализа экономических новостей";
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
  muted: "555F5B",
  green: "0F5132",
  light: "EDF3F0",
  grid: "B7C6C0",
  blue: "1F3A5F",
  white: "FFFFFF",
};

function addFooter(slide, n) {
  slide.addText(`${STUDENT} · ${GROUP} · ${n}/12`, {
    x: 0.55, y: 7.08, w: 12.2, h: 0.22,
    fontFace: "Arial", fontSize: 8.5, color: C.muted, align: "right",
  });
}

function title(slide, text, subtitle, n) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.green }, line: { color: C.green } });
  slide.addText(text, {
    x: 0.65, y: 0.45, w: 11.4, h: 0.72,
    fontFace: "Arial", fontSize: 25, bold: true, color: C.ink,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.67, y: 1.16, w: 10.8, h: 0.35,
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

function sectionLabel(slide, text, x, y, w = 2.0) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h: 0.34,
    fill: { color: C.green },
    line: { color: C.green },
  });
  slide.addText(text, {
    x: x + 0.08, y: y + 0.08, w: w - 0.16, h: 0.12,
    fontFace: "Arial", fontSize: 8.5, bold: true, color: C.white,
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
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.72, fill: { color: C.green }, line: { color: C.green } });
slide.addText(UNIVERSITY, {
  x: 0.75, y: 0.24, w: 11.8, h: 0.2,
  fontFace: "Arial", fontSize: 10.5, bold: true, color: C.white,
  align: "center", margin: 0,
});
slide.addText("КУРСОВАЯ РАБОТА", {
  x: 0.75, y: 1.32, w: 11.8, h: 0.28,
  fontFace: "Arial", fontSize: 14, bold: true, color: C.green,
  align: "center", margin: 0,
});
slide.addText("Разработка автоматической диалоговой системы\nна основе языковой модели для анализа\nэкономических новостей", {
  x: 1.1, y: 1.9, w: 11.1, h: 1.55,
  fontFace: "Arial", fontSize: 28, bold: true, color: C.ink,
  align: "center", margin: 0, fit: "shrink",
});
slide.addText(`Выполнил: ${STUDENT}\nГруппа: ${GROUP}\nРуководитель: ____________________`, {
  x: 7.15, y: 4.25, w: 4.9, h: 0.85,
  fontFace: "Arial", fontSize: 13, color: C.ink,
  margin: 0, breakLine: false,
});
slide.addShape(pptx.ShapeType.line, { x: 1.1, y: 5.7, w: 11.1, h: 0, line: { color: C.grid, width: 1 } });
slide.addText("Москва, 2026", {
  x: 0.75, y: 6.26, w: 11.8, h: 0.22,
  fontFace: "Arial", fontSize: 12, color: C.muted,
  align: "center", margin: 0,
});
addFooter(slide, 1);
slide.addNotes("Тема работы и общий результат: локальная система, которая отвечает на вопросы по экономическим новостям и показывает источники.");

slide = pptx.addSlide();
title(slide, "Актуальность", "Пользователю нужен быстрый ответ по множеству экономических сообщений", 2);
sectionLabel(slide, "Критерий: введение / актуальность", 0.8, 1.55, 2.8);
bulletList(slide, [
  "Экономические новости быстро меняют ожидания рынка.",
  "Ручной анализ множества источников занимает время.",
  "Диалоговый формат снижает порог входа.",
  "Ответ должен опираться на найденные источники, а не только на общие знания модели.",
], 0.8, 2.0, 5.5, 2.8, 18);
addPipeline(slide, ["много новостей", "вопрос", "поиск", "анализ", "ответ"], 5.25);

slide = pptx.addSlide();
title(slide, "Цель и задачи", "Цель: найти новости, оценить влияние и сформировать ответ", 3);
sectionLabel(slide, "Критерий: введение / цель и задачи", 0.8, 1.52, 3.0);
slide.addText("ML/NLP-часть", {
  x: 0.9, y: 1.95, w: 4.7, h: 0.3,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Определить текстовое представление новостей.",
  "Реализовать retrieval/RAG по источникам.",
  "Реализовать классификацию влияния новости.",
  "Поддержать template и LLM-режим ответа.",
], 0.9, 2.38, 5.0, 2.4, 15.5);
slide.addText("Backend-часть", {
  x: 6.55, y: 1.95, w: 4.7, h: 0.3,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Спроектировать микросервисную DDD-архитектуру.",
  "Реализовать асинхронные сервисы и фоновые задачи.",
  "Сделать React UI с SSE timeline.",
  "Подготовить Docker Compose demo-сценарий.",
], 6.55, 2.38, 5.2, 2.4, 15.5);
slide.addText("Баланс защиты: примерно 50% ML/NLP и 50% production backend", {
  x: 0.9, y: 5.55, w: 10.8, h: 0.35,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.blue, margin: 0,
});

slide = pptx.addSlide();
title(slide, "Общая архитектура", "Каждый сервис отвечает за отдельную часть диалогового сценария", 4);
sectionLabel(slide, "Критерий: методы и результаты", 0.55, 1.22, 2.6);
slide.addImage({ path: path.join(assetsDir, "architecture-diagram.png"), x: 0.55, y: 1.55, w: 12.1, h: 5.2 });

slide = pptx.addSlide();
title(slide, "Pipeline обработки вопроса", "ML/NLP pipeline выполняется внутри асинхронного backend-сценария", 5);
sectionLabel(slide, "Критерий: методы и результаты", 0.8, 1.55, 2.6);
addPipeline(slide, ["вопрос", "retrieval", "analysis", "dialog", "источники", "ответ"], 2.05);
bulletList(slide, [
  "ML/NLP: поиск контекста, score источников, классификация влияния.",
  "Backend: gateway, сервисные контракты, SSE-события и orchestration.",
  "Ответ строится только по найденным новостям и явно показывает источники.",
], 0.9, 3.55, 5.6, 2.0, 15.5);
bulletList(slide, [
  "chat_started",
  "search_started / sources_found",
  "analysis_started / analysis_completed",
  "answer_started / answer_completed / done",
], 7.1, 3.55, 4.7, 2.0, 15.5);

slide = pptx.addSlide();
title(slide, "Методы и технологии", "Стек разделен на ML/NLP-методы и backend-инфраструктуру", 6);
sectionLabel(slide, "Критерий: методы и результаты", 0.9, 1.22, 2.6);
addTableLike(slide, [
  ["Часть", "Выбор"],
  ["ML: текстовые признаки", "TF-IDF, embeddings"],
  ["ML: классификация", "Logistic Regression, tiny transformer mode"],
  ["NLP: retrieval/RAG", "Qdrant + контекст источников"],
  ["NLP: генерация", "Template fallback + LLM adapter"],
  ["Backend", "FastAPI, asyncio, Granian, Zapros"],
  ["Архитектура", "DDD, слои, Protocol, Dishka"],
  ["Очереди и события", "Taskiq, Redis, FastStream, SSE"],
  ["UI и запуск", "React, Docker Compose, Justfile"],
], 0.9, 1.5, [3.35, 7.45], 0.5);

slide = pptx.addSlide();
title(slide, "ML/NLP-компоненты", "Анализ новости сделан как объяснимый baseline с расширяемыми режимами", 7);
sectionLabel(slide, "Критерий: методы и результаты", 0.8, 1.48, 2.6);
slide.addText("Классификация влияния", {
  x: 0.9, y: 1.9, w: 4.8, h: 0.28,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Классы: positive, negative, neutral.",
  "Baseline: TF-IDF + Logistic Regression.",
  "Выход: impact, confidence, explanation.",
  "Расширение: embedding-logreg и tiny-transformer-classifier.",
], 0.9, 2.27, 5.2, 2.35, 15.2);
slide.addText("Retrieval и генерация", {
  x: 6.55, y: 1.9, w: 4.8, h: 0.28,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Qdrant хранит документы и векторные представления.",
  "Ответ строится по top-k источникам.",
  "Template generator дает стабильный demo.",
  "LLM-режим подключает Qwen3-0.6B-Instruct-GGUF через llama.cpp.",
], 6.55, 2.27, 5.4, 2.35, 15.2);
slide.addText("MLflow используется как точка учета экспериментов, метрик и артефактов моделей.", {
  x: 0.9, y: 5.5, w: 10.8, h: 0.35,
  fontFace: "Arial", fontSize: 14.5, bold: true, color: C.blue, margin: 0,
});

slide = pptx.addSlide();
title(slide, "Интерфейс приложения", "Пользователь видит ответ, источники и timeline обработки", 8);
sectionLabel(slide, "Критерий: методы и результаты", 0.55, 1.18, 2.6);
slide.addImage({ path: path.join(assetsDir, "ui-demo-screenshot.png"), x: 0.55, y: 1.45, w: 12.2, h: 5.3 });

slide = pptx.addSlide();
title(slide, "Результаты проверки", "Demo smoke подтверждает end-to-end сценарий", 9);
sectionLabel(slide, "Критерий: методы и результаты", 0.9, 1.18, 2.6);
addTableLike(slide, [
  ["Проверка", "Результат"],
  ["api-gateway health", "ok"],
  ["news-service health", "ok"],
  ["CSV preview", "5 документов"],
  ["index CSV", "5 документов"],
  ["Taskiq job", "queued"],
  ["retrieval + analysis", "источники + impact"],
  ["chat SSE", "8 событий"],
  ["frontend HTML", "ok"],
], 0.9, 1.5, [4.0, 5.5], 0.5);
slide.addText("Команды: just demo-up → just demo-smoke → just demo-down", {
  x: 0.9, y: 6.25, w: 9.8, h: 0.35,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});

slide = pptx.addSlide();
title(slide, "Соответствие теме", "Все ключевые части темы закрыты реализованным сценарием", 10);
sectionLabel(slide, "Критерий: методы и результаты", 0.8, 1.32, 2.6);
addTableLike(slide, [
  ["Требование темы", "Что реализовано"],
  ["Автоматическая диалоговая система", "Web UI + chat SSE endpoint"],
  ["Языковая модель", "LLM-адаптер в dialog-service"],
  ["ML-анализ новостей", "tfidf-logreg, impact, confidence, explanation"],
  ["Retrieval/RAG", "top-k источники, score, Qdrant"],
  ["Production backend", "FastAPI, DDD, Dishka, Taskiq, Redis"],
  ["Воспроизводимый результат", "Docker Compose + smoke-сценарий"],
], 0.8, 1.65, [4.7, 6.5], 0.6);

slide = pptx.addSlide();
title(slide, "Заключение", "Результат объединяет ML/NLP pipeline и production backend", 11);
sectionLabel(slide, "Критерий: заключение", 0.8, 1.48, 1.8);
slide.addText("ML/NLP-результат", {
  x: 0.9, y: 1.82, w: 4.6, h: 0.3,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Поиск релевантного контекста.",
  "Классификация влияния новостей.",
  "Ответ по источникам с LLM-адаптером.",
  "MLflow для дальнейших экспериментов.",
], 0.9, 2.2, 5.0, 2.45, 15.5);
slide.addText("Backend-результат", {
  x: 6.55, y: 1.82, w: 4.6, h: 0.3,
  fontFace: "Arial", fontSize: 15, bold: true, color: C.green, margin: 0,
});
bulletList(slide, [
  "Микросервисы со слоистой DDD-структурой.",
  "Асинхронные API, фоновые задачи и SSE.",
  "React UI и Docker Compose запуск.",
  "Smoke-сценарий для проверки стенда.",
], 6.55, 2.2, 5.1, 2.45, 15.5);
slide.addText("Дальнейшее развитие: реальные news API, расширение датасета, сравнение моделей и сохранение истории диалогов.", {
  x: 0.9, y: 5.45, w: 10.8, h: 0.42,
  fontFace: "Arial", fontSize: 14.2, bold: true, color: C.blue, margin: 0,
});

slide = pptx.addSlide();
title(slide, "Источники", "Документация технологий и базовые материалы по NLP/архитектуре", 12);
sectionLabel(slide, "Критерий: список источников", 0.8, 1.48, 2.1);
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
