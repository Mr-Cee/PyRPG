# db_init.py

from sqlalchemy import create_engine
from models import Base

DATABASE_URL = "postgresql+psycopg2://PyRPG_Admin:Christie91!@localhost/PyRPG"

engine = create_engine(DATABASE_URL)

def init_db():
    Base.metadata.create_all(engine)
    print("✅ Database initialized!")

if __name__ == "__main__":
    init_db()