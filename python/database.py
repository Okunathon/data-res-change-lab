import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:Lolster22!@localhost:5432/myapp'
)
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db():
    from models import ChatSession
    Base.metadata.create_all(bind=engine)
    ensure_chat_sessions_schema()


def ensure_chat_sessions_schema():
    inspector = inspect(engine)
    if 'chat_sessions' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('chat_sessions')}
    statements = []

    if 'created_at' not in existing_columns:
        if engine.dialect.name == 'postgresql':
            statements.append(
                "ALTER TABLE chat_sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        else:
            statements.append(
                "ALTER TABLE chat_sessions ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
