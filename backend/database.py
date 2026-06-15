# Module de connexion a la base de donnees.
# On utilise SQLAlchemy comme ORM pour gerer les modeles et les sessions.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# SQLite necessite un argument special pour fonctionner en mode multi-thread.
# En production (PostgreSQL), ce parametre n'est pas necessaire.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Creation du moteur de connexion a la base de donnees
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

# Fabrique de sessions. Chaque requete API recoit sa propre session.
# autocommit=False : on controle manuellement les transactions.
# autoflush=False : les changements ne sont envoyes en base que lors du commit.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base pour la declaration des modeles SQLAlchemy
Base = declarative_base()

def get_db():
    """Generateur de session de base de donnees.
    Utilise comme dependance FastAPI pour injecter une session dans chaque endpoint.
    La session est automatiquement fermee apres utilisation."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
