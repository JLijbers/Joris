import os
import git
import threading
from flask_socketio import SocketIO, emit

socketio = SocketIO()
git_feedback_received = threading.Event()


class GitManager:
    def __init__(self):
        self.repo = None
        self.commit_message = "Auto-commit"

    def set_directory(self, repo_path):
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            print("Initializing the application's directory as a new Git repository..")
            self.repo = git.Repo.init(repo_path)
            self.commit_changes(message="Initial commit")

    def is_dirty(self):
        return self.repo.is_dirty()

    def stage_changes(self):
        self.repo.git.add(A=True)

    def discard_changes(self):
        self.repo.git.reset('--hard')
        self.repo.git.clean('-fdx')

    def set_commit_message(self, summary, description=None):
        self.commit_message = summary
        if description:
            self.commit_message += "\n\n" + description
        self.update_prepare_commit_msg_hook()

    def update_prepare_commit_msg_hook(self):
        hook_path = os.path.join(self.repo.git_dir, 'hooks', 'prepare-commit-msg')
        hook_content = f"""#!/bin/sh
            echo "{self.commit_message}" > "$1"
            """
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        os.chmod(hook_path, 0o755)  # Make the hook executable

    def commit_changes(self, message=None):
        self.stage_changes()
        if message is None:
            message = self.commit_message if self.commit_message else "Auto-commit"
        self.repo.index.commit(message)

    def handle_dirty_repo(self):
        if self.is_dirty():
            emit('script_output', {'data': "The Git repository has uncommitted changes."})
            emit('request_git_feedback_dirty', {'message': "Choose an action:"})
            git_feedback_received.wait()

    def remove_msg_hook(self):
        hook_path = os.path.join(self.repo.git_dir, 'hooks', 'prepare-commit-msg')
        if os.path.exists(hook_path):
            os.remove(hook_path)


def finalize_git_feedback():
    git_feedback_received.set()
