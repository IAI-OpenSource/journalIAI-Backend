# GitHub Copilot Instructions – Journal IAI Backend

## 🎯 Objectif du projet
Backend SaaS développé avec **FastAPI**, **SQLAlchemy Async (PostgreSQL)**, **Pydantic**, **Celery**, **Redis**, **MiniIO**.  
Ce projet est un mini-facebook pour une université et gère les **etudiants, posts, clubs, medias..**.  
L’objectif est d’obtenir un code propre, optimisé et bien commenté tout en maintenant la cohérence sur l’ensemble du projet.

---

## 🧩 Stack & conventions principales
- **Langage :** Python 3.12+
- **Framework :** FastAPI
- **ORM :** SQLAlchemy Async
- **Base de données :**PostgreSQL**
- **Validation :** Pydantic
- **Style de code :**
  - Code Object-Oriented (classes pour les services, repositories, etc.)
  - Code organisé de manière très modulaire (routers, services, repositories, models, schemas)
  - Nommage en **snake_case**
  - Fonctions **courtes**, explicites et cohérentes
  - **Docstrings** au format **Google Style**
  - Commentaires clairs sur la logique métier importante
  - Typage strict (`-> Type`) sur toutes les fonctions

---

## 🧠 Attentes envers Copilot

### 1. Cohérence et patterns
Copilot doit suivre les patterns déjà présents dans le codebase :
- Reprendre les conventions de nommage et structures FastAPI existantes.  
- Proposer des signatures de fonctions avec types explicites.  
- Prioriser l’usage de **async / await** pour les opérations base de données.  
- Suggérer des **imports déjà utilisés ailleurs** plutôt que d’en inventer de nouveaux.

⚙️ Les models de la bd se trouvent dans "app/db/models"

**Exemple attendu :**
```python
async def getPersonnelByEmail(db: AsyncSession, email: str) -> Optional[Personnel]:
    """Récupère un personnel par son adresse email."""
    query = select(Personnel).where(Personnel.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()

2. Fonctions CRUD (priorité élevée)

Copilot doit générer des fonctions CRUD asynchrones avec :

Gestion d’erreurs (IntegrityError, NoResultFound)

Retour clair du modèle ou None

Commentaires indiquant l’intention métier

Respect des transactions (async with db.begin())

Bon exemple :

async def createPersonnel(db: AsyncSession, data: PersonnelCreate) -> Personnel:
    """Crée un nouveau personnel dans la base."""
    new_personnel = Personnel(**data.dict())
    db.add(new_personnel)
    await db.commit()
    await db.refresh(new_personnel)
    return new_personnel

3. Schémas Pydantic

Copilot doit proposer :

Des modèles clairs héritant de BaseModel

Des Config internes pour alias et ORM mode

Des docstrings explicites pour chaque champ important

Exemple :

class PersonnelBase(BaseModel):
    """Modèle de base pour le personnel."""
    nom: str
    email: EmailStr
    poste: Optional[str] = None

    class Config:
        orm_mode = True

4. Endpoints FastAPI documentés

Copilot doit générer des routes FastAPI avec :

Décorateurs explicites (@router.get, @router.post, etc.)

Docstrings contenant le résumé

Utilisation cohérente des modèles de réponse et de requête

Exemple :

@router.post("/personnels", response_model=PersonnelRead, status_code=status.HTTP_201_CREATED)
async def create_personnel(data: PersonnelCreate, db: AsyncSession = Depends(get_db)):
    """
    Crée un nouveau personnel.

    Args:
        data (PersonnelCreate): Données du personnel.
        db (AsyncSession): Session de base de données.

    Returns:
        PersonnelRead: Données du personnel créé.
    """
    return await createPersonnel(db, data)

5. Comportement attendu

✅ Favoriser la cohérence du code plutôt que la nouveauté.

✅ Suggérer du code commenté, clair, et prêt à être testé.

❌ Ne pas inventer de modèles ou routes non existantes.

❌ Éviter les import inutiles ou doublons.

⚙️ Peut s’adapter au contexte (Copilot peut simplifier ou détailler selon la fonction).
