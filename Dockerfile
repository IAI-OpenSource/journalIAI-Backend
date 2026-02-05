FROM python:3.12-slim AS base
LABEL authors="sevtify"

ENTRYPOINT ["top", "-b"]