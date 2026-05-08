# Render QA Note

Автоматическая структурная проверка Office-файлов выполнена:

- `.docx` открывается как OOXML-пакет;
- `.pptx` открывается как OOXML-пакет;
- в `.docx` найдено 66 параграфов, 3 таблицы и 2 изображения;
- в `.pptx` найдено 12 слайдов и 3 media-объекта;
- demo smoke приложения выполнен успешно.

Визуальный render-gate через `render_docx.py` не выполнен, потому что на
локальной машине отсутствует `soffice` / LibreOffice. Команда завершилась
ошибкой `FileNotFoundError: soffice`.

Перед финальной сдачей рекомендуется открыть:

- `docs/final/coursework-explanatory-note.docx`;
- `docs/final/coursework-defense-presentation.pptx`;

и заполнить титульные данные: ФИО, группу, руководителя и образовательную
организацию.
