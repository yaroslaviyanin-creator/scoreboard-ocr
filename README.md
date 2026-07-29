# Scoreboard OCR Tracker v2

Кроссплатформенное приложение для распознавания табло с веб-камеры и вывода результатов в текстовые файлы для vMix и других программ наложения графики.

Работает на **Windows 10/11** и **macOS** (включая Apple Silicon).

## Возможности

- Захват видео с любой веб-камеры
- Рисование прямоугольных зон (ROI) прямо на видео: счёт, время, названия команд
- 4 режима распознавания: `Standard`, `Time`, `Name`, `7-segment`
- Стабилизация результатов (значение фиксируется только после 2 одинаковых циклов)
- Атомарная запись в `.txt` файлы — vMix никогда не увидит половину файла
- Шаблоны цифр: можно «обучить» приложение на конкретном шрифте табло
- Сохранение/загрузка пресетов (JSON) с шаблонами
- Панель отладки OCR в реальном времени
- Полное логирование всех ошибок — ничего не проглатывается молча

## Требования

- Python 3.11+
- Tesseract OCR:
 - **macOS**: `brew install tesseract`
 - **Windows**: [скачать установщик](https://github.com/UB-Mannheim/tesseract/wiki) или скопировать папку `Tesseract-OCR/` рядом с .exe

## Установка для разработки

```bash
git clone <repo-url>
cd scoreboard_ocr
pip install -e ".[dev]"
```

## Запуск из исходников

```bash
python -m scoreboard_ocr.app
```

## Запуск тестов

```bash
pytest
```

## Сборка в исполняемый файл

### macOS

```bash
pyinstaller build/macos.spec
# Результат: dist/ScoreboardOCR.app
```

При первом запуске может потребоваться «Открыть» через контекстное меню (Gatekeeper).
Для распространения нужна нотаризация Apple (см. TODO в `build/macos.spec`).

### Windows

```bash
pyinstaller build/windows.spec
# Результат: dist/ScoreboardOCR/
```

Перед сборкой на Windows скопируйте папку `Tesseract-OCR/` (установленный Tesseract) в корень проекта, чтобы она попала в бандл.

## Структура проекта

```
scoreboard_ocr/
├── pyproject.toml
├── README.md
├── .github/workflows/tests.yml    # CI (pytest на Windows + macOS, build по тегам)
├── build/
│   ├── windows.spec               # PyInstaller spec для Windows
│   └── macos.spec                 # PyInstaller spec для macOS
├── src/scoreboard_ocr/
│   ├── app.py                     # Точка входа
│   ├── platform_utils.py          # Кроссплатформенные утилиты
│   ├── logging_setup.py           # Настройка логирования
│   ├── video/                     # Камеры и видеопоток
│   ├── roi/                       # Интерактивные зоны (QRect + диалог настроек)
│   ├── recognition/               # OCR-движок (абстракция + бэкенды)
│   ├── presets/                   # Загрузка/сохранение пресетов
│   ├── output/                    # Атомарная запись .txt
│   └── ui/                        # Главное окно и панель отладки
├── tests/                         # pytest тесты
├── docs/                          # Документация
└── templates/                     # Шаблоны цифр (0.png..9.png)
```

## Формат вывода

Для каждой зоны с именем `Name` создаётся файл `Name.txt` в выбранной папке.
Файл содержит только распознанное значение, без кавычек и переводов строк.
Запись атомарная (temp + rename) — внешние программы всегда видят целый файл.

## Лицензия

MIT
