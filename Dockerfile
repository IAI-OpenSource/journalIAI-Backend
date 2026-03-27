# --- Étape 1 : Base commune ---
FROM python:3.11-slim AS builder

ENV WORKDIR=/app
# Empêche Python de générer des fichiers .pyc et d'utiliser un buffer pour les logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR $WORKDIR

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
# On doit redéfinir la variable dans le stage 2
ENV WORKDIR=/app

WORKDIR $WORKDIR

# Installation de ffmpeg, libmagic1 pour le traitement image/vidéo et libpq-dev pour PostgreSQL
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*


# Récupération des libs installées au stage précédent
COPY --from=builder /install /usr/local
COPY . .

# Les ports seront défini par le service dans docker-compose.yml
