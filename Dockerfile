FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH \
    PORT=7860

RUN useradd --create-home --uid 1000 appuser

USER appuser
WORKDIR $HOME/app

COPY --chown=appuser:appuser requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=appuser:appuser . .
RUN mkdir -p storage/logs

EXPOSE 7860

CMD ["python", "main.py"]
