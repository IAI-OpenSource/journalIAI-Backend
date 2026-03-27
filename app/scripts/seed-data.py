import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal as SessionLocal 
from app.db.models.academic_year import AcademicYear
from app.db.models.classe import Classe
from app.db.models.enums import ClasseType

async def seed():
    async with SessionLocal() as session:
        # Création de l'année académique
        year = AcademicYear(
            libelle="2023-2024",
            start_date=datetime(2023, 9, 1),
            end_date=datetime(2024, 7, 31)
        )
        session.add(year)
        await session.flush() # Pour obtenir l'ID de year

        # Création d'une classe
        new_classe = Classe(
            classe_prefix=ClasseType.TC2, # Utilisez votre Enum
            classe_suffix="E",
            academic_year_id=year.id
        )
        session.add(new_classe)
        
        await session.commit()
        print("Données insérées avec succès !")

if __name__ == "__main__":
    asyncio.run(seed())