import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

project_root = Path(__file__).resolve().parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv('DATABASE_URL') or f"sqlite:///{project_root / 'pitch_simulator.db'}"

engine_options = {}
if DATABASE_URL.startswith('sqlite'):
    engine_options['connect_args'] = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, **engine_options)

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
