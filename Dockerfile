# --- Étape 1 : Base commune ---
FROM python:3.11-slim AS builder

ENV WORKDIR=/fast_api_app
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

WORKDIR $WORKDIR

# Installation de ffmpeg pour le traitement image/vidéo et libpq-dev pour PostgreSQL
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


# Récupération des libs installées au stage précédent
COPY --from=builder /install /usr/local
COPY . .

# Sécurité : On ne lance pas l'app en root
# On crée un utilisateur non-root pour la sécurité
# Création du dossier de logs avec les permissions appropriées
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p logs && chown -R appuser:appuser /app


# Changer pour l'utilisateur non-root
USER appuser

# Les ports seront défini par le service dans docker-compose.yml
