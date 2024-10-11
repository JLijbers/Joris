from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from codebase.codebase_class import Base
from llm.llm_calls import refine_user_story, relevant_code, generate_instructions, generate_code


class UserStory(Base):
    __tablename__ = 'user_stories'

    id = Column(Integer, primary_key=True)
    jira_id = Column(String)
    original_story = Column(String)
    refined_story = Column(String)
    relevant_files = Column(String)
    instructions = Column(String)
    generated_code = Column(String)
    status = Column(String)

    # Define relationship with codebase
    codebase_id = Column(Integer, ForeignKey('codebases.id'))
    codebase = relationship('Codebase', back_populates='user_stories')

    def __init__(self, jira_id, vectordb, original_story):
        self.id = None  # This will be set when the user story is saved to the database
        self.jira_id = str(jira_id)
        self.original_story = original_story
        self.vectordb = vectordb
        self.refined_story = None
        self.relevant_files = None
        self.instructions = None
        self.generated_code = None
        self.status = "to_pick_up"

    def refine_user_story(self, codebase_description, user_id, models):
        self.refined_story = refine_user_story(self.original_story, codebase_description, user_id, models)
        self.status = "user_story_refined"

    def relevant_code(self, folder_structure, summary, models):
        self.relevant_files = relevant_code(self.original_story, self.refined_story, folder_structure, summary, models)
        self.status = "relevant_files_identified"

    def generate_instructions(self, models):
        self.instructions = generate_instructions(self.vectordb, self.refined_story, self.relevant_files, models)
        self.status = "instructions_generated"

    def generate_code(self, models):
        self.generated_code = generate_code(self.vectordb, self.instructions, self.refined_story, models)
        self.status = "code_generated"
