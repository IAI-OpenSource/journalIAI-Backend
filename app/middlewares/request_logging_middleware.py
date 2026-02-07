import time
import logging
from starlette.responses import Response
from fastapi import Request

logger = logging.getLogger("request")


async def log_requests(request: Request, call_next) -> Response:
    """
    Middleware pour logger les requêtes entrantes, leur méthode, leur url, leur status code et le temps
    de traitement de la requete, apres on pourra rajouter d'autres infos si besoin, comme l'ip du client,
    les headers, etc... et on pourra meme exposer une route pour consulter les logs de requetes, ou les envoyer a
    un service de monitoring externe comme LogStash, elasticsarch, graffana etc...
    Args:
        request: Requête entrante
        call_next: Fonction qui va appeler le prochain middleware ou endpoint dans la chaîne de traitement de la requête

    Returns:
        Response: La réponse générée par le prochain middleware ou endpoint

    """
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )
    
    if duration > 1:
      logger.warning("REQUÊTE LENTE: %s %s (%ss)", request.method, request.url.path, duration)

    return response
