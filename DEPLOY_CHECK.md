Deploy IAI JOurnal:

- Ajouter des limites CPU au niveau des workers pour ne pas bloqueer tout le cpu, notamment au niveau des uploads:
  services:
  worker:
  build: .
  command: celery -A app.worker.celery worker --loglevel=info -Q high-priority,default
  deploy:
  resources:
  limits:
  cpus: '1.5' # On laisse 1.5 cœur sur 4 pour le transcodage
  memory: 1G
  # ... reste de la config
- Parametrer les limites par rapport à la puissance réelle du serveur de deployement,
- Ajuster les limites en conséquence pour éviter les problèmes de performance.
    
    