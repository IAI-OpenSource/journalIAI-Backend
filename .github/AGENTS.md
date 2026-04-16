# AI Agents Guide – Journal IAI Backend

## 📋 Project Overview

**Journal IAI** is a university mini-social-network SaaS backend built with **FastAPI**, **SQLAlchemy Async**, **PostgreSQL**, **Celery**, **Redis**, and **MiniIO**. The application manages students, posts, clubs, events, stories, and media with a focus on clean, modular, well-typed code.

**Key entities:** User, Post, Club, Event, Story, Academic Year, Classe, Notification.

---

## 🏗️ Architecture & Module Structure

### Core Layers

```
app/
├── routers/           # FastAPI endpoint handlers (HTTP layer)
├── services/          # Business logic + orchestration
├── repositories/      # Data access layer (CRUD operations)
├── db/
│   ├── models/        # SQLAlchemy ORM models
│   ├── base.py        # SQLAlchemy engine setup
│   └── session.py     # AsyncSession factory (get_db dependency)
├── schemas/           # Pydantic validation models
├── cache/             # Redis caching layer
├── storage/           # MiniIO media storage abstraction
├── auth/              # JWT, roles, security
├── worker/            # Celery task definitions
└── core/              # Configuration, logging
```

### Critical Data Flow

1. **HTTP Request** → `router` (FastAPI endpoint)
2. **Router** → creates `Service` (with injected db + cache)
3. **Service** → calls `Repository` methods for DB queries
4. **Repository** → executes SQLAlchemy queries, returns `CRUDResult[T]`
5. **Service** → wraps result in `ServiceResult[T]` with status codes
6. **Router** → converts to `ApiBaseResponse[T]` for HTTP response

---

## 🎯 Critical Patterns & Conventions

### 1. Result Wrapper Pattern (Essential)

All database operations must return typed result objects:

- **Repository layer:** Returns `CRUDResult[T]` (wraps data/error + status_code)
- **Service layer:** Returns `ServiceResult[T]` (wraps data/error + status_code + service_name)
- **Router layer:** Converts to `ApiBaseResponse[T]` (ok/result/error for API clients)

```python
# Repository example
async def get_user_by_id(self, user_id: UUID) -> CRUDResult[User]:
    query = select(User).where(User.id == user_id)
    result = await self.db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        return CRUDResult.crud_error("User not found", status_code=404)
    return CRUDResult.crud_success(data=user, status_code=200)

# Service example
async def service_get_user(self, user_id: UUID) -> ServiceResult[ReadUser]:
    result = await self.__user_repo.get_user_by_id(user_id)
    if result.is_error():
        return ServiceResult.service_error(result.error, status_code=result.status_code)
    return ServiceResult.service_success(ReadUser.from_orm(result.data), status_code=200)
```

**Import locations:**
- `from app.repositories import CRUDResult`
- `from app.services import ServiceResult`
- `from app.schemas import ApiBaseResponse`

### 2. Async/Await Everywhere (for DB)

All database operations must be async:

```python
# ✅ Correct
async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[User]:
    query = select(User).where(User.id == id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

# ❌ Wrong
def get_by_id(self, db: AsyncSession, id: UUID):
    ...  # Missing async/await
```

**Session injection:** Use `AsyncSession` from FastAPI dependencies (see `get_db` in `app/db/session.py`).

### 3. Repository as Dataclass

Repositories are lightweight dataclasses initialized with `db: AsyncSession`:

```python
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class PostRepository:
    db: AsyncSession
    
    async def insert_post(self, post_data: CreatePost) -> CRUDResult[Post]:
        new_post = Post(**post_data.dict())
        self.db.add(new_post)
        try:
            await self.db.commit()
            await self.db.refresh(new_post)
            return CRUDResult.crud_success(new_post, status_code=201)
        except IntegrityError as e:
            await self.db.rollback()
            return CRUDResult.crud_error("Duplicate or invalid data", status_code=409)
```

**Never instantiate directly in routers/services.** Always inject via dataclass constructor.

### 4. Service with Dependency Injection

Services hold `__db`, `__repo`, and cache references as private attributes:

```python
class UserService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__user_cache = UserCache(cache)
        self.__user_repo = UserRepository(self.__db)
    
    async def service_find_user(self, user_id: UUID) -> ServiceResult[ReadUser]:
        # Check cache first
        cached = await self.__user_cache.get_user_from_cache(user_id)
        if cached:
            return ServiceResult.service_success(cached, status_code=200)
        # Fallback to DB
        result = await self.__user_repo.get_user_by_id(user_id)
        ...
```

**Service naming:** `service_<action>_<entity>()` (e.g., `service_create_post`, `service_get_all_users`).

### 5. Router Dependency Injection & FastAPI Structure

Routers use FastAPI dependencies to inject services:

```python
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.cache.helpers.base import get_redis

router = APIRouter(
    prefix="/user",
    tags=[ApiTags.USER],
    dependencies=[Depends(RoleDepends.all_authorize)]
)

def get_user_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheWrapper = Depends(get_redis)
) -> UserService:
    return UserService(db, cache)

@router.get("/{user_id}", response_model=ReadUser)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service)
):
    result = await user_service.service_find_user(user_id)
    return result.to_HTTP_api_base_response(Response())
```

**Key patterns:**
- Use `Depends()` for injecting services, db, cache.
- `response_model=` for Pydantic output validation.
- `Depends(RoleDepends.*)` for role-based access control.
- Always convert `ServiceResult` to `ApiBaseResponse` before returning.

### 6. Pydantic Schemas with ORM Mode

Define separate read/write schemas with consistent naming:

```python
class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str
    bio: Optional[str] = None

class CreateUser(UserBase):
    """Schema for user creation."""
    password: str = Field(min_length=8)
    jeton: FindRegistration  # Registration token validation

class ReadUser(UserBase):
    """Schema for user read operations."""
    id: UUID
    email: EmailStr
    created_at: datetime
    
    class Config:
        from_attributes = True  # ORM mode (Pydantic v2)

class UpdateUserData(BaseModel):
    """Schema for user updates (only modifiable fields)."""
    username: Optional[str] = None
    bio: Optional[str] = None
```

**Naming convention:**
- `Create<Entity>`: For POST/PUT requests.
- `Read<Entity>`: For GET responses.
- `Update<Entity>Data`: For PATCH requests (partial updates only).

### 7. SQLAlchemy Models with Constraints

Models use declarative column names (constraint constants) for clarity:

```python
from sqlalchemy import DateTime, ForeignKey, Index, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

FK_USERS_CLASSE = "fk_users_classe"
IDX_USERS_CREATED_AT_ID = "idx_users_created_at_id"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    classe_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("classes.id", name=FK_USERS_CLASSE),
        nullable=True
    )
    
    __table_args__ = (
        Index(IDX_USERS_CREATED_AT_ID, "created_at", "id"),
    )
```

**Best practices:**
- Use `Mapped[Type]` for type hints (SQLAlchemy 2.0 style).
- Define constraint names as module-level constants.
- Use `deleted_at` for soft deletes, not hard deletes.
- Add indexes for frequently queried columns (avoid N+1 problems).

### 8. Error Handling & IntegrityError Mixin

Repositories catch SQLAlchemy errors (duplicates, FK violations):

```python
try:
    self.db.add(new_user)
    await self.db.commit()
    await self.db.refresh(new_user)
    return CRUDResult.crud_success(new_user, status_code=201)
except IntegrityError as e:
    await self.db.rollback()
    # IntegrityMapperMixin provides human-readable error mapping
    error_msg = self.handle_integrity_error(e)
    return CRUDResult.crud_error(error_msg, status_code=409)
```

**IntegrityMapperMixin location:** `app/db/models/mixins/integrity_error_mixin.py`  
All models should inherit from both `Base` and `IntegrityMapperMixin`.

### 9. Caching Layer (Redis)

Cache operations are abstracted into model-specific cache classes:

```python
# app/cache/user_cache.py
class UserCache:
    def __init__(self, cache: CacheWrapper):
        self.__cache = cache
    
    async def get_user_from_cache(self, user_id: UUID, model: Type[T]) -> Optional[T]:
        """Try to get user from Redis cache."""
        cached_json = await self.__cache.get(f"user:{user_id}")
        if cached_json:
            return model.model_validate_json(cached_json)
        return None
    
    async def set_user_cache(self, user_id: UUID, user_data: BaseModel, ttl: int):
        """Store user in Redis cache."""
        await self.__cache.set(
            f"user:{user_id}",
            user_data.model_dump_json(),
            ex=ttl
        )
```

**Cache durations:** Defined in `app/globals/cache_duration.py`.  
**Pattern:** Check cache first → if miss, query DB → update cache → return.

### 10. Media Storage (MiniIO)

File uploads/downloads are handled through `MediaUploadStorage` and `MediaReadStorage`:

```python
# For generating upload URLs
upload_storage = MediaUploadStorage()
upload_url = await upload_storage.generate_presigned_upload_url(
    bucket="user-avatars",
    object_key=f"{user_id}/avatar.jpg",
    expires_seconds=3600
)

# For generating download URLs
read_storage = MediaReadStorage()
download_url = await read_storage.get_download_url(
    bucket="user-avatars",
    object_key=f"{user_id}/avatar.jpg"
)
```

**Location:** `app/storage/media_upload_storage.py`, `app/storage/media_read_storage.py`.  
**Celery tasks** are triggered for async media processing (see `app/worker/tasks/`).

### 11. Async Tasks with Celery

Long-running operations (media processing, notifications) use Celery:

```python
# app/worker/tasks/user_avatar_process_task.py
from app.worker.celery_app import celery_app

@celery_app.task(name="process_user_avatar")
def process_user_avatar_task(user_id: str, image_path: str):
    """Async task to process and compress user avatar."""
    # Run intensive operations here
    ...

# Called from router/service:
from app.worker.tasks.user_avatar_process_task import process_user_avatar_task

process_user_avatar_task.delay(str(user_id), image_path)  # Async enqueue
```

**Celery config:** `app/worker/celery_app.py`  
**Beat scheduler:** `celery_beat_schedule` defined in `celery_app` for periodic tasks.

### 12. Global Constants & Messages

Reusable constants are centralized:

```python
# app/globals/status_codes.py
class StatusCode(Enum):
    _200_STATUS_SUCCESS = 200
    _201_CREATED = 201
    _400_BAD_REQUEST = 400
    _401_UNAUTHORIZED = 401
    _403_FORBIDDEN = 403
    _404_NOT_FOUND = 404
    _409_CONFLICT = 409
    _500_INTERNAL_ERROR = 500

# app/globals/messages.py
class Messages:
    USER_NOT_FOUND = "Utilisateur non trouvé"
    INVALID_CREDENTIALS = "Email ou mot de passe incorrect"
    ...

# app/globals/api_tags.py
class ApiTags:
    USER = "User"
    POST = "Post"
    ...
```

**Always use these instead of hardcoding strings!**

---

## 📂 File Organization Rules

### Naming Conventions

- **snake_case** for all identifiers (functions, variables, files).
- **PascalCase** for classes.
- **UPPER_CASE** for constants.
- Files grouped by entity: `user_service.py`, `user_repository.py`, `user_schemas.py`, `user_router.py`.

### Docstring Format (Google Style)

```python
async def create_post(db: AsyncSession, data: CreatePost) -> CRUDResult[Post]:
    """Créé un nouveau post dans la base.
    
    Args:
        db (AsyncSession): Session de base de données.
        data (CreatePost): Données de création du post.
    
    Returns:
        CRUDResult[Post]: Résultat de l'opération avec le post créé ou erreur.
    
    Raises:
        IntegrityError: Si les contraintes d'intégrité sont violées.
    """
```

### Function Characteristics

- **Short & focused:** Each function does one thing.
- **Explicit return types:** Always include `-> Type` annotation.
- **Defensive checks:** Handle None, empty lists, invalid states early.
- **Consistent error messages:** Use `app/globals/messages.py`.

---

## 🔧 Developer Workflows

### Database Migrations (Alembic)

```bash
# Generate migration from model changes
make migrate-gen msg="Add new field to users"

# Apply migrations
make migrate-up

# Rollback one migration
make migrate-down
```

**Key files:**
- `alembic.ini`: Alembic configuration.
- `alembic/versions/`: Migration scripts (auto-generated).
- Models are in `app/db/models/`, Alembic watches them.

### Running the Server

```bash
# Docker Compose (recommended)
make start_docker
make stop_docker
make restart_api

# Local (Python 3.12+)
python -m uvicorn app.main:app --reload --port 8000
```

**Server start:** Uses lifespan context manager in `app/main.py` to run setup (logging, etc.).

### Testing & Debugging

- **Request logging:** Middleware logs all HTTP requests (see `app/middlewares/request_logging_middleware.py`).
- **Health check:** `GET /health` (no auth required).
- **API docs:** `GET /docs` (Swagger UI auto-generated).

### Celery Tasks

```bash
# Start worker
celery -A app.worker.celery_app worker --loglevel=info

# Start Celery Beat (scheduler)
celery -A app.worker.celery_app beat --loglevel=info
```

---

## ⚠️ Common Pitfalls & Patterns to Avoid

| ❌ Wrong | ✅ Correct | Reason |
|---------|-----------|--------|
| `def get_user():` (no async) | `async def get_user():` | DB ops must be async |
| Hardcoded status codes | Use `StatusCode` enum | Centralized, testable |
| Returning raw SQLAlchemy models | Wrap in `CRUDResult` | Consistent error handling |
| Services calling services directly | Use repositories → services | Clear separation of concerns |
| Importing from wrong modules | Follow layer structure (repos don't import services) | Prevents circular imports |
| Forgetting `await` on queries | Always `await db.execute(query)` | Ensures async execution |
| No cache check before DB query | Check cache → DB → update cache | Reduces DB load |
| Hardcoded Pydantic `orm_mode=True` | Use `from_attributes=True` (Pydantic v2) | Modern Pydantic syntax |
| Creating Service outside dependency | Use `Depends(get_service)` | FastAPI manages lifecycle |

---

## 🚀 Getting Started as an AI Agent

1. **Understand the flow:** Pick an existing feature (e.g., user creation) and trace it: router → service → repository → model.
2. **Find patterns:** Look at `UserRepository`, `UserService`, `user_router.py` as templates.
3. **Replicate structure:** New entity? Copy patterns from User to maintain consistency.
4. **Use type hints:** Every function must have input and output types.
5. **Reference messages/status codes:** Always use `app/globals/` constants, never hardcode.
6. **Test locally:** Run `make start_docker` and hit `/docs` to verify endpoints.
7. **Check migrations:** After model changes, run `make migrate-gen`.

---

## 📚 Key Files to Reference

- **Architecture:** `app/main.py` (FastAPI setup), `app/routers/base_router.py` (router composition)
- **Result types:** `app/repositories/__init__.py`, `app/services/__init__.py`
- **DB setup:** `app/db/base.py`, `app/db/session.py`
- **Example implementations:** `app/services/user_service.py`, `app/routers/user_router.py`
- **Global constants:** `app/globals/` (messages, status codes, cache durations, tags)
- **Celery:** `app/worker/celery_app.py`, `app/worker/tasks/`
- **Auth:** `app/auth/role_depends.py` for role-based access control

---

**Last updated:** 2026-04-15  
**Stack:** Python 3.12+, FastAPI, SQLAlchemy Async, PostgreSQL, Redis, Celery, MiniIO

