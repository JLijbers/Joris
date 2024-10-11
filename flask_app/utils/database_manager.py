import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager

from codebase.codebase_class import Codebase, Base
from userstory.userstory_class import UserStory


class DatabaseManager:
    def __init__(self, db_name, db_base_path):
        db_path = os.path.join(db_base_path, db_name)
        db_url = f'sqlite:///{db_path}'
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """Initialize the database schema."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_or_update_codebase(self, session, codebase: Codebase):
        existing_codebase = session.query(Codebase).filter(Codebase.name == codebase.name).one_or_none()
        if existing_codebase:
            # Update existing codebase
            existing_codebase.folder_structure = codebase.folder_structure
            existing_codebase.summary = codebase.summary
            existing_codebase.description = codebase.description
            session.merge(existing_codebase)
        else:
            # Add new codebase
            session.add(codebase)
        session.commit()

    def update_user_story(self, session, user_story: UserStory):
        session.merge(user_story)
        session.commit()

    def add_user_story(self, session, codebase_name: str, user_story: UserStory):
        codebase = session.query(Codebase).filter(Codebase.name == codebase_name).one()
        user_story.codebase = codebase
        session.add(user_story)
        session.commit()

    def get_codebase(self, session, codebase_name: str):
        return session.query(Codebase).filter(Codebase.name == codebase_name).one_or_none()

    def get_user_story(self, session, codebase_name: str, current_user_story: str):
        codebase = session.query(Codebase).filter(Codebase.name == codebase_name).one()
        return session.query(UserStory).filter(
            UserStory.codebase_id == codebase.id,
            UserStory.original_story == current_user_story
        ).one_or_none()

    def get_all_project_names(self, session):
        return [codebase.name for codebase in session.query(Codebase).all()]
