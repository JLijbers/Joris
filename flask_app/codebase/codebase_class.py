import os
import json
import time

from config import IGNORE_PATH

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from llm.llm_calls import summarize, describe_application

Base = declarative_base()


class Codebase(Base):
    __tablename__ = 'codebases'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    directory = Column(String)
    folder_structure = Column(String)
    summary = Column(String)
    description = Column(String)
    ignore_file_path = Column(String)

    user_stories = relationship('UserStory', back_populates='codebase')

    def __init__(self, name, directory, ignore_file_path=IGNORE_PATH):
        self.id = None
        self.name = name
        self.directory = directory
        self.summary = None
        self.description = None
        self.ignore_file_path = ignore_file_path
        self.folder_structure = self.extract_folder_structure()

    @property
    def ignore_config(self):
        return self._load_ignore_config()

    def _load_ignore_config(self):
        try:
            with open(self.ignore_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Ignore file not found at {self.ignore_file_path}. Using empty configuration.")
            return {'ignored_directories': [], 'ignored_files': [], 'ignored_extensions': []}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in ignore file at {self.ignore_file_path}. Using empty configuration.")
            return {'ignored_directories': [], 'ignored_files': [], 'ignored_extensions': []}

    def extract_folder_structure(self):
        ignored_directories = set(self.ignore_config.get('ignored_directories', []))

        def extract_structure(path, indent=""):
            result = []
            folder_name = os.path.basename(path)

            if folder_name in ignored_directories:
                return []

            result.append(f"{indent}{folder_name}/")

            if os.path.isdir(path):
                try:
                    items = sorted(os.listdir(path))
                    for item in items:
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            result.extend(extract_structure(item_path, indent + "  "))
                        else:
                            result.append(f"{indent}  {item}")
                except PermissionError:
                    result.append(f"{indent}  [Permission Denied]")
                except Exception as e:
                    result.append(f"{indent}  [Error: {str(e)}]")

            return result

        return "\n".join(extract_structure(self.directory))

    def generate_summary(self, models):
        print("Summarizing codebase..")
        result = []

        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignore_config.get('ignored_directories', [])]

            for file in files:
                if file in self.ignore_config.get('ignored_files', []) or \
                   any(file.endswith(ext) for ext in self.ignore_config.get('ignored_extensions', [])):
                    continue

                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    summary = summarize(content, models)
                    result.append(f"File: {os.path.basename(file)}\nSummary of file: {summary}\n")
                except Exception as e:
                    result.append(f"File: {os.path.basename(file)}\nError summarizing file: {str(e)}\n")

        self.summary = "\n".join(result)
        return self.summary

    def update_summary(self, models):
        print("Updating codebase summary for recently changed files...")

        # Get the current time
        now = time.time()
        time_ago = now - 180

        # Split existing summary into parts
        updated_summary_parts = self.summary.split("\n\nFile: ")
        updated_summary_parts[0] = updated_summary_parts[0][6:]

        # Create a map of filenames to their summaries
        summary_map = {}
        for part in updated_summary_parts:
            file_name, summary = part.split('\n', 1)
            summary_map[file_name] = f"File: {file_name}\n{summary}"

        # Recursively traverse the directory and its subdirectories
        for root, dirs, files in os.walk(self.directory):
            # Skip directories and files specified in ignore configurations
            dirs[:] = [d for d in dirs if d not in self.ignore_config.get('ignored_directories', [])]
            files[:] = [f for f in files if f not in self.ignore_config.get('ignored_files', []) and not any(
                f.endswith(ext) for ext in self.ignore_config.get('ignored_directories', []))]

            for file in files:
                # Create the full path to the current file
                path = os.path.join(root, file)

                # Check if the file was modified within the last 3 minutes
                if os.path.getmtime(path) >= time_ago:
                    # Open the file and read its content
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Start summarization
                    new_summary = summarize(content, models)

                    # Update the summary in the map
                    summary_map[file] = f"File: {file}\n{new_summary}"

        # Rebuild the updated summary from the map
        self.summary = "\n\n".join(summary_map.values())

        return self.summary

    def describe_application(self, models):
        self.description = describe_application(self.summary, self.folder_structure, models)
        return self.description
