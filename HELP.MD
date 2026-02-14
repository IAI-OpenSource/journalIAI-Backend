# HELP — Architecture et exemple d'utilisation

But: Expliquer l'architecture complète du backend "journalIAI-Backend" et fournir un exemple end-to-end (schemas → repository → service → router)

Plan d'action

- [x] Présenter l'architecture et les responsabilités des répertoires/fichiers clés
- [x] Décrire précisément le flux de données (requête → réponse)
- [x] Fournir un exemple concret et raisonnable (schemas, repository, service, router) intégré dans le document
- [x] Expliquer le typage avec `CRUDResult` et les patterns d'erreurs
- [x] Indiquer tests / next steps (parties laissées intentionnellement comme placeholders)

Contrat et conventions

- Conventions du projet : FastAPI, SQLAlchemy Async, Pydantic, typage strict, async/await, docstrings Google style.
- Le code fourni dans les exemples est à titre illustratif et doit être adapté au contexte réel (modèles DB, logique métier spécifique).
- L'objectif est de fournir un guide clair pour les développeurs qui souhaitent contribuer au projet, en respectant les patterns et l'architecture existants.
- Toutes les fonctions et classes doivent être documentées avec des docstrings explicatives, et les erreurs doivent être gérées de manière cohérente.

1) Vue d'ensemble de l'architecture

Structure principale (résumé)

- `app/main.py` : point d'entrée FastAPI (initialisation de l'app, montage des routers, middlewares, event hooks).
- `app/core/` : configuration et logging (`config.py`, `logging_config.py`).
- `app/db/` : configuration de la DB et session async (`session.py`), modèles SQLAlchemy dans `app/db/models/`.
- `app/repositories/` : couche d'accès aux données. Contient `CRUDResult` (typage des retours CRUD) et d'autres repos spécifiques (per modèle).
- `app/services/` : logique métier orchestrant plusieurs repositories et comportements transactionnels (appelée par les routers), contient aussi `ServiceResult` si besoin (Meme utilisation que CrudResult).
- `app/schemas/` : modèles Pydantic (request/response) exposés par les endpoints.
- `app/routers/` : routeurs FastAPI; ils valident la requête et appellent les services.
- `app/middlewares/` : middlewares (ex: `request_logging_middleware.py`).
- `app/worker/` : tâches asynchrones (Celery) et workers (ex: `celery_app.py`).
- `app/globals/` : constantes partagées, messages, tags API, résultat standard `GlobalAppResult`.

Responsabilités par couche

- Routers : validation d'entrée (Pydantic), contrôle d'accès, conversion des erreurs en réponses HTTP (status codes).
- Services : règles métiers (transactions, orchestration, validation complexe, publishing d'événements, appels aux repositories) ils retournent `ServiceResult[T]` qui sera transformé en réponse HTTP et renvoyé au client.
- Repositories : opérations CRUD atomiques contre la DB (SQLAlchemy Async). Ils retournent `CRUDResult[T]` pour un contrat clair.
- DB models : définitions ORM. Les migrations sont gérées dans `alembic/`.

2) Flux de données détaillé (requête → réponse)

1. Le client envoie une requête HTTP vers l'API (ex: POST /posts).
2. FastAPI route la requête via un router situé dans `app/routers/`.
3. Le router dé-sérialise la requête en Pydantic schema (ex: `PostCreate`) et injecte la dépendance `db: AsyncSession` (via `Depends(get_db)`).
4. Le router appelle la méthode du service correspondant (ex: `post_service.create_post(...)`).
5. Le service implémente la logique métier : validation complémentaire, gestion des transactions si besoin, orchestration d'appels à un ou plusieurs repositories (ex: `post_repo.create_post`, `media_repo.attach_media`) et publication éventuelle d'événements Celery.
6. Les repositories effectuent les requêtes SQLAlchemy (select, insert, update, delete) en mode async, gèrent les exceptions DB (IntegrityError, NoResultFound), et retournent `CRUDResult` pour décrire le résultat.
7. Le service transforme le `CRUDResult` en un objet `ServiceResult` adaptée.
8. Le router retourne un modèle de réponse Pydantic (`PostRead`) en exploitant `ServiceResult` et un code HTTP approprié (201, 200, 404, 400...).
9. Middleware et logging interceptent et enregistrent la requête/réponse si configurés.

Diagramme simplifié (conceptuel)

Client -> Router -> Service -> Repository -> DB
                             ^
                             +-- Worker/Celery (pour tâches asynchrones)

3) Contrats et patterns recommandés

Contrat léger pour les repositories (exprimé en mots)

- Entrées : `db: AsyncSession` (ou session injectable), et un DTO/Schema Pydantic ou arguments simples.
- Sortie : `CRUDResult[T]` où T est le modèle retourné (ex: `Post`, `User`).
- Erreurs DB traitées : IntegrityError (doublons, FK), NoResultFound (sélection vide).
- Gestion transactionnelle : flush, commit, rollback gérés dans le service ou dans le repository selon la complexité de l'opération.

Exemple de signature attendue (style du projet)

- Repository
  - async def create_post(db: AsyncSession, data: PostCreate) -> CRUDResult[Post]:
  - async def get_post_by_id(db: AsyncSession, post_id: int) -> CRUDResult[Post]:

- Service
  - async def create_post(db: AsyncSession, data: PostCreate) -> ServiceResult[PostRead]

- Router
  - @router.post("/posts", response_model=PostRead)
    async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db))

4) `CRUDResult` — Typage des retours CRUD

La classe `CRUDResult` fournie encapsule un résultat de succès (donnée) ou une erreur (message). Le pattern consiste à :

- Retourner `CRUDResult.crud_success(obj)` en cas de succès
- Retourner `CRUDResult.crud_error("message")` en cas d'échec métier ou d'exception interceptée

Le service consomme le `CRUDResult` et transforme à son tour en `ServiceResult` ou lève une `HTTPException` avec un code et message approprié.

4)b) `ServiceResult` - Typage des retours de la couche service
- Similaire à `CRUDResult` mais pour la couche service, il peut encapsuler des données de sortie prêtes à être converties en réponse HTTP
- Permet de séparer les préoccupations : `CRUDResult` pour la couche repository, `ServiceResult` pour la couche service, et les exceptions HTTP pour la couche router.

5) Exemple complet (cas concret) : Gestion simple des Posts

Contexte choisi : API pour créer et récupérer un post.

Objectifs de l'exemple

- Montrer des schemas Pydantic (request/response)
- Montrer un repository minimal qui interagit avec SQLAlchemy Async et retourne `CRUDResult`.
- Montrer un service orchestrant la création et la récupération.
- Montrer un router FastAPI exposant les endpoints POST /posts et GET /posts/{id}.

Remarque : le code ci-dessous est un exemple didactique. Il doit être adapté au modèle SQLAlchemy réel (noms de colonnes, relations). Aucune modification de votre codebase n'est faite ici : tout est contenu dans ce document.

---

Exemple : Post (extrait documentaire)

Finalement j'ai enlevé les exemples de code pour ne pas faire de modification dans la codebase, mais l'idée est d'avoir un exemple complet qui suit le flux décrit (schemas → repository → service → router) avec des commentaires expliquant chaque étape.


7) Contrats, exceptions et gestion d'erreurs recommandés

- Toujours transformer les erreurs DB en messages lisibles avant de les exposer.
- Logguer les exceptions détaillées côté serveur (stack trace) mais renvoyer un message non verbeux au client.
- Utiliser les codes HTTP standards : 201 (création), 400 (erreur validation / business), 404 (non trouvé), 409 (conflit), 500 (erreur interne).

8) Quality gates (liste de contrôle avant pull-request)

- Code Quality : SonarQube
- Type-checker : mypy si vous voulez souffir ou juste respecter le typage strict demandé
- Vérifier `alembic` si modèles DB modifiés

9) Points d'attention spécifiques à ce repo

- Utilisation intensive d'`async/await` : ne pas appeler de fonctions bloquantes dans les handlers.
- `app/repositories/__init__.py` expose `CRUDResult` — l'utiliser systématiquement pour typer les retours des repos.
- `app/db/session.py` contient typiquement `get_db()` — s'assurer que la dépendance est asynchrone et yield la session correctement.
- `app/worker/` et Celery : isoler les effets secondaires (ex: upload vers MinIO, envoi de mails) dans des tâches asynchrones.

10) Next steps suggérés

- Ajouter des templates de repository/service pour chaque entité (User, Post, Club) afin d'assurer la cohérence.
- Créer un dossier `docs/` ou `CONTRIBUTING.md` qui reprend ce HELP avec exemples adaptables.
- Écrire des tests d'intégration basiques pour les endpoints critiques (auth, posts, upload media).

Annexes

- Référence `CRUDResult` (extrait de `app/repositories/__init__.py`)

```
class CRUDResult(GlobalAppResult[T]):
    """Classe générique pour typer les réponses d'opérations CRUD dans le Repository."""

    def __init__(self, data: Optional[T] = None, error: Optional[str] = None):
        super().__init__(data, error)

    @classmethod
    def crud_success(cls, data: T):
        return cls(data=data)

    @classmethod
    def crud_error(cls, message: str):
        return cls(error=message)
```

- Liste des fichiers et dossiers importants (rappel)

```
app/
  main.py
  core/ (config, logging)
  db/ (models/, session.py, base.py)
  repositories/ (CRUDResult + repos)
  services/ (ServiceResult + services)
  schemas/
  routers/
  middlewares/
  worker/ (celery)
  globals/ (messages, api_tags)
```

Fin du document — HELP