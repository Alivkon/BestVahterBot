FROM python:3.10-slim

WORKDIR /app

# Сначала зависимости — они кэшируются, пока requirements не изменился
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код бота (.env в образ НЕ попадает — см. .dockerignore)
COPY bestvahterbot.py bestvahterbot_words.py ./

# Непривилегированный пользователь (uid 1001 совпадает с владельцем папки на хосте,
# чтобы volume ./data был доступен на запись)
RUN useradd --create-home --uid 1001 botuser && chown -R botuser /app
USER botuser

CMD ["python", "-u", "bestvahterbot.py"]
