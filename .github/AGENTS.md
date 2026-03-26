# AGENTS.md – Journal IAI Backend

AI agents should read this before making code changes. This documents the architecture, patterns, and workflows specific to this SaaS backend.

## 🎯 Project Context

**Type:** FastAPI SaaS backend for a university social platform ("Journal IAI").  
**Core Domain:** Students, posts, clubs, events, media, comments, moderation, and user roles.  
**Tech Stack:** FastAPI + SQLAlchemy Async (PostgreSQL) + Pydantic + Celery + Redis + MinIO + Alembic.  
**Python:** 3.12+ with uvloop for optimized async performance.

---

## 🏗️ Architecture & Data Flows

### 1. **Layered Architecture (Router → Service → Repository → Model)**

The codebase follows strict separation of concerns across four layers:

- **Router** (`app/routers/`): HTTP endpoints, request/response handling.
- **Service** (`app/services/`): Business logic, orchestration, cache management.
- **Repository** (`app/repositories/`): Database queries (DAO pattern), transaction handling.
- **Model** (`app/db/models/`): SQLAlchemy ORM definitions.

**Key Flow Example:**
```
POST /v1/users/{id}
  → base_router includes v1_api_router (app/routers/base_router.py)
  → Route handler calls UserService.service_find_user_by_id()
  → Service checks UserCache (Redis via CacheWrapper)
  → If miss, calls UserRepository.get_user_by_id() (SQL query)
  → Repository returns CRUDResult[User] (success/error wrapper)
  → Service returns ServiceResult[ReadUser] (validated schema)
  → Route returns JSON via ApiBaseResponse wrapper
```

**See:** `app/routers/base_router.py` (shows router composition), `app/services/user_service.py`, `app/repositories/user_repository.py`.

### 2. **Result Wrappers (GlobalAppResult & Subclasses)**

All operations return **typed result objects** instead of throwing exceptions (fail-fast patterns).

- `CRUDResult[T]` (repositories): Wraps DB operation success/error with HTTP status codes.
- `ServiceResult[T]` (services): Wraps business logic result with service metadata.
- `GlobalAppResult[T]` (base class): Abstract wrapper in `app/globals/app_result.py`.

**Usage Pattern:**
```python
result = await self.user_repo.get_user_by_id(user_id)
if result.is_error():
    return ServiceResult.service_error(message=result.error, status_code=result.status_code)
return ServiceResult.service_success(result.data, status_code=result.status_code)
```

### 3. **Cache Layer (Redis + CacheWrapper)**

Services use Redis for caching via `CacheWrapper` (dependency injection pattern).

- **Cache Classes:** `UserCache`, `PostCache`, `ClubCache`, `SessionCache`, etc. in `app/cache/`.
- **Cache Keys:** Generated via `CacheKeysFactory` with standardized key patterns.
- **TTL:** Defined in `app/globals/cache_duration.py` (e.g., `CacheDurartion.USER_DURATION`).

**Example Flow in UserService:**
```python
# Try cache first (Redis)
user_data = await self.user_cache.get_user_from_cache(user_id, ReadUser)
if user_data is not None:
    return ServiceResult.service_success(user_data)

# Fall back to database
user = await self.user_repo.get_user_by_id(user_id)

# Update cache with database result
await self.user_cache.set_user_in_cache(user_id, user_read, ttl=CacheDurartion.USER_DURATION.value)
```

See: `app/cache/user_cache.py`, `app/cache/cache_utils.py`.

### 4. **External Services & Dependencies**

- **PostgreSQL:** Async via SQLAlchemy + asyncpg driver (`app/db/`).
- **Redis:** Broker + cache via async-redis (`REDIS_URL` in config).
- **MinIO:** S3-compatible object storage for media (`app/storage/` pattern expected).
- **Celery:** Task queue (workers/celery tasks expected, not yet in routers).
- **JWT + Cookies:** Auth via `python-jose` + argon2 for password hashing (`app/auth/`).

See: `docker-compose.yml` for service orchestration, `app/core/config.py` for environment vars.

---

## 📋 Critical Patterns & Conventions

### 1. **Model Definition & Indexes**

Models live in `app/db/models/` and use SQLAlchemy 2.0 Mapped syntax with advanced indexing.

**Key Patterns:**
- `UUID` primary keys (defaults to `uuid.uuid4()`).
- `DateTime(timezone=True)` for timestamps (server-side defaults via `func.now()`).
- **Soft delete:** `deleted_at` column for logical deletion; queries filter `WHERE deleted_at IS NULL`.
- **Constraints:** Named check constraints (e.g., `CHK_USERS_BIO_LENGTH`), unique constraints.
- **Relationships:** Use `relationship()` with lazy loading strategies.
- **Indexes:** Define in `__table_args__` with `postgresql_where` for conditional indexes on non-deleted rows.

**Example (User Model):**
```python
class User(Base, IntegrityMapperMixin):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, init=False)
    
    __table_args__ = (
        Index(IDX_USERS_EMAIL, "email", postgresql_where=(deleted_at == None)),
        CheckConstraint("LENGTH(bio) <= 500", name=CHK_USERS_BIO_LENGTH),
    )
```

### 2. **Pydantic Schemas (Request/Response)**

Schemas inherit from `BaseModel` and include ORM mode for SQLAlchemy integration.

**Naming Convention:**
- `CreateXxx`: For POST/write operations (no `id`, `created_at`).
- `ReadXxx`: For GET responses (includes all read-only fields).
- `UpdateXxx`: For PATCH operations (optional fields).

**Example:**
```python
class CreateUser(BaseModel):
    last_name: str
    email: EmailStr
    password: str

class ReadUser(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    
    class Config:
        orm_mode = True
```

See: `app/schemas/user_schemas.py`, `app/schemas/classe_schemas.py`.

### 3. **Repository Functions (CRUD Operations)**

Repositories handle **all** database access and must:
- Use async/await syntax.
- Return `CRUDResult[T]` (never throw SQLAlchemy exceptions to callers).
- Catch `IntegrityError` and delegate to `RepositoriesUtils.traiter_integrity_error()`.
- Use `select()` builder with `joinedload()` or `selectinload()` for eager loading.
- Manage transactions explicitly (`await db.commit()` or `await db.rollback()`).

**Pattern:**
```python
async def get_user_by_id(self, user_id: UUID) -> CRUDResult[User]:
    try:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return CRUDResult.crud_error(msg.USER_NOT_FOUND, status._404_STATUS_NOT_FOUND.value)
        return CRUDResult.crud_success(user, status._200_STATUS_SUCCESS.value)
    except IntegrityError as ie:
        return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)
```

See: `app/repositories/user_repository.py`, `app/repositories/repositories_utils.py`.

### 4. **Service Layer & Dependency Injection**

Services orchestrate repositories and caches. Constructor receives `AsyncSession` and `CacheWrapper`:

```python
class UserService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.user_cache = UserCache(cache)
        self.user_repo = UserRepository(self.db)
```

Services use **async methods** prefixed with `service_` (e.g., `service_find_user_by_id()`). Always return `ServiceResult[T]`.

See: `app/services/user_service.py`, `app/services/registration_service.py`.

### 5. **Enums for Type Safety**

Use SQLAlchemy enums (from `app/db/models/enums.py`) for constrained values:

```python
class UserRole(str, Enum):
    STUDENT = "STUDENT"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"

class SexeType(str, Enum):
    F = "F"
    M = "M"
```

In models: `role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT)`.

See: `app/db/models/enums.py`.

### 6. **Router Composition**

Routers are organized by resource and included in `app/routers/base_router.py`:

```python
v1_api_router = APIRouter(prefix="/v1")
v1_api_router.include_router(post_video_upload_router)
# More routers included here
```

Each router endpoint:
- Declares `response_model` (Pydantic schema).
- Uses `Depends(get_db)` for `AsyncSession` injection.
- Returns `ApiBaseResponse[T]` wrapper or raw schema.

See: `app/routers/base_router.py`, `app/routers/post_video_upload_router.py`.

---

## 🔧 Developer Workflows & Commands

### Database Migrations (Alembic)

Alembic manages schema changes. Use these **Makefile targets** in Docker:

```bash
# Generate migration (autogenerate based on model changes)
make migrate-gen msg="Add user bio field"

# Apply all pending migrations
make migrate-up

# Rollback one migration
make migrate-down

# Build and restart services
make rebuild_docker
make start_docker
```

**Key Files:**
- `alembic.ini`: Configuration.
- `alembic/versions/`: Migration scripts.
- `app/db/models/`: ORM models (Alembic watches these).

### Local Development

```bash
# Start all services (PostgreSQL, Redis, MinIO, API)
make start_docker

# Restart only the API (after code changes)
make restart_api

# View logs
docker compose logs -f api

# Run in development mode (if not using Docker)
python -m uvicorn app.main:app --reload --port 8000
```

### Environment Setup

Configuration is loaded from `.env` file (see `app/core/config.py`):

```env
ENVIRONMENT=LOCAL
DATABASE_USER=postgres
DATABASE_PASSWORD=...
DATABASE_NAME=journal_iai
DATABASE_HOST=db
REDIS_URL=redis://redis:6379/0
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=...
SECRET_KEY=...
JWT_EXPIRES_MINUTES=30
```

---

## 🚨 Common Integration Points & Edge Cases

### 1. **IntegrityError Handling**

When a unique constraint or foreign key fails, catch `IntegrityError` and use:

```python
from app.repositories.repositories_utils import RepositoriesUtils

try:
    # ... db operation ...
except IntegrityError as ie:
    return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)
```

This utility extracts the constraint name from PostgreSQL error and returns a human-readable message.

### 2. **Soft Delete Logic**

Never hard-delete. Instead, set `deleted_at`:

```python
user.deleted_at = func.now()
await db.commit()
```

Always filter queries: `where(Model.deleted_at == None)`. Indexes use `postgresql_where=(deleted_at == None)`.

### 3. **Async Session Management**

Sessions are provided via dependency:

```python
@router.get("/users/{user_id}")
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user = await UserService(db, cache).service_find_user_by_id(user_id)
    return user
```

**Never** manage sessions manually in routes; use `get_db` from `app/db/session.py`.

### 4. **Cache Invalidation**

After mutations (create/update/delete), explicitly invalidate related caches:

```python
# After creating a post:
await self.post_cache.invalidate_user_posts_cache(user_id)
await self.user_cache.invalidate_user_stats_cache(user_id)
```

### 5. **Relationship Loading**

Use `joinedload()` or `selectinload()` to avoid N+1 queries:

```python
stmt = select(Post).options(
    joinedload(Post.author),
    selectinload(Post.media)
)
```

---

## 📁 File Structure Quick Reference

```
app/
├── auth/                    # JWT, cookies, auth dependencies
├── cache/                   # Redis caching layer (UserCache, PostCache, etc.)
├── core/                    # Config, logging setup
├── db/
│   ├── models/             # SQLAlchemy ORM models (User, Post, Club, etc.)
│   ├── session.py          # AsyncSessionLocal, get_db()
│   └── base.py             # SQLAlchemy Base class, engine setup
├── globals/                # Constants (status_codes.py, messages.py, cache_duration.py)
├── middlewares/            # Request logging, CORS
├── repositories/           # DAO layer (UserRepository, PostRepository, etc.)
├── routers/                # FastAPI routers (base_router.py orchestrates)
├── schemas/                # Pydantic request/response models
├── services/               # Business logic (UserService, PostService, etc.)
├── storage/                # MinIO/S3 integration (expected structure)
├── utils/                  # Shared utilities
└── main.py                 # FastAPI app, lifespan setup

alembic/
├── versions/               # Migration scripts (auto-generated)
└── env.py                  # Alembic configuration
```

---

## 🎯 Coding Standards Specific to This Project

1. **Naming Convention:** `snake_case` for functions/variables, `PascalCase` for classes.
2. **Type Hints:** Always use `-> ReturnType` on functions; use `Optional[T]` for nullable fields.
3. **Docstrings:** Google Style (brief one-liner, then Args/Returns/Raises).
4. **Async First:** All DB operations must use `async/await`.
5. **Error Handling:** Return `*Result[T]` wrappers, never raise exceptions across layers.
6. **No Hardcoded Values:** Use `app/globals/` (status codes, messages, cache durations).
7. **Database Soft Delete:** Always check `deleted_at` in queries.
8. **Cache Management:** Centralize cache logic in `app/cache/` classes; invalidate on mutations.

---

## 🔗 Key Files to Review First

- `app/main.py` — Entry point, lifespan setup, middleware registration.
- `app/db/models/user.py` — Reference model with indexes, constraints, soft delete.
- `app/repositories/user_repository.py` — Reference repository with error handling.
- `app/services/user_service.py` — Reference service with cache + DB coordination.
- `app/routers/base_router.py` — Router composition pattern.
- `app/globals/app_result.py` — Result wrapper pattern.
- `.github/copilot-instructions.md` — Original AI instructions (supplement to this file).

---

**Last Updated:** March 2026  
**For Questions:** Review existing patterns in named files or `docker-compose.yml` for deployment context.

