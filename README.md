# BestVahterBot

Телеграм-бот [@BestVahterBot](https://t.me/BestVahterBot) — модератор чата:

- удаляет сообщения с запрещёнными словами (список — в `bestvahterbot_words.py`);
- уведомляет администратора;
- запоминает чаты, в которых работает (список хранится в `data/chats.json`);
- запускается в Docker-контейнере с автоперезапуском.

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие: возможности бота и число чатов, где он работает |
| `/add слово1, слово2, ...` | **Только для администратора.** Добавить запрещённые слова. Слова разделяются запятыми, точками с запятой или переносами строк. Слова хранятся в `data/extra_words.json` и переживают перезапуск. Пример: `/add продажа батов, накрутка подписчиков` |

## Требования

- Python 3.x (или Docker + Docker Compose)

## Настройка

Секреты (токен бота, ID администратора) лежат в файле `.env` в корне проекта.
Шаблон — [.env.example](.env.example).

> ⚠️ Файл `.env` не копировать в git и в Docker-образ — он уже исключён через `.gitignore` и `.dockerignore`.

```bash
cp .env.example .env
# заполните токен бота и ID администратора
```

После смены токена в `.env` перезапустите контейнер: `docker compose up -d`.

## Запуск (docker compose)

```bash
cd /opt/bots/BestVahterBot

docker compose up -d            # запустить (или применить изменения .env/compose)
docker compose up -d --build    # пересобрать образ и запустить (после правок кода)
docker compose restart          # простой перезапуск контейнера
docker compose stop             # остановить
docker compose down             # остановить и удалить контейнер/сеть
```

## Логи и статус

```bash
docker compose logs -f bestvahter-bot   # смотреть логи (Ctrl+C для выхода)
docker compose logs --tail 50           # последние 50 строк
docker ps --filter name=bestvahter_bot  # статус контейнера
```

## Автозапуск

Контейнер создан с `restart: always` — при перезагрузке сервера бот стартует
сам вместе со службой Docker, а при падении автоматически перезапускается.
Ничего дополнительно делать не нужно.

## Запуск без Docker (не рекомендуется, для отладки)

```bash
cd /opt/bots/BestVahterBot
python bestvahterbot.py
```
