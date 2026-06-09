# Деплой сайта

## Что загружать

Для демонстрации сайта на Python-хостинге нужны:

- `server.py`
- все `*.html`, `*.css`, `*.js`
- папки `foto`, `uploads`, `.data`
- `Procfile`
- `requirements.txt`

Не нужны для работы сайта:

- `.venv`
- `.vscode`
- `tools`
- `doctor_accounts.txt`
- `database.sql`
- `api.php`
- `config.php`

## Локальный запуск

```bash
python server.py
```

Открыть:

```text
http://127.0.0.1:8000
```

## Хостинг

Нужен Python-хостинг, где можно запустить команду:

```bash
python server.py
```

Сервер сам возьмет порт из переменной окружения `PORT`, если хостинг ее задает.

## Важно

Для показа проекта проще всего использовать VPS или Python-хостинг. Обычный PHP-хостинг подойдет только если отдельно переносить проект на PHP/MySQL.
