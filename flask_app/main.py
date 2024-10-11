import os
import configparser
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO

import create_project as create_project
import open_project as open_project
import setup_application as setup_application
from utils.git_manager import GitManager
from utils.database_manager import DatabaseManager
from config import STATIC_PATH, TEMPLATE_PATH, CONFIG_PATH, DATABASE_PATH

app = Flask(__name__,
            static_folder=STATIC_PATH,
            template_folder=TEMPLATE_PATH)

app.secret_key = 'supersecretkey'

socketio = SocketIO(app, cors_allowed_origins='*')

# GitManager
app.git_manager = GitManager()

# DatabaseManager
if not os.path.exists(DATABASE_PATH):
    os.makedirs(DATABASE_PATH)
app.db_manager = DatabaseManager('database.db', DATABASE_PATH)
app.db_manager.init_db()

# Register blueprints
app.register_blueprint(setup_application.setup_bp)
app.register_blueprint(create_project.create_project_bp)
app.register_blueprint(open_project.open_project_bp)

# Dummy user data
users = {"test_user": "12345"}


def get_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return config


def is_login_disabled():
    config = get_config()
    return config.getboolean('DEFAULT', 'disable_login', fallback=False)


@app.route('/')
def index():
    if is_login_disabled():
        return redirect(url_for('main'))
    return render_template('LoginPage.html')


@app.route('/main')
def main():
    try:
        with app.db_manager.session_scope() as db_session:
            project_names = app.db_manager.get_all_project_names(db_session)
    except Exception:
        project_names = []

    if 'username' in session or is_login_disabled():
        return render_template('MainPage.html', user_id=session.get('username', 'Developer'),
                               project_names=project_names)
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_login_disabled():
        return redirect(url_for('main'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('main'))
        else:
            return render_template('LoginPage.html', error=True)
    return render_template('LoginPage.html')


# Register SocketIO event handlers
@socketio.on('save_settings')
def handle_save_settings(json):
    setup_application.handle_save_settings(json, socketio)


@socketio.on('create_project')
def handle_create_project(json):
    create_project.handle_create_project(json, socketio)


@socketio.on('add_user_story')
def handle_add_user_story(json):
    open_project.handle_add_user_story(json)


@socketio.on('delete_user_story')
def handle_delete_user_story(json):
    open_project.handle_delete_user_story(json)


@socketio.on('jira_import')
def handle_jira_import(json):
    open_project.import_jira_issues(json, socketio)


@socketio.on('run_story')
def handle_run_story(json):
    open_project.handle_run_story(json, socketio)


@socketio.on('git_feedback_dirty')
def on_git_feedback_dirty(json):
    open_project.on_git_feedback_dirty(json, socketio)


@socketio.on('user_story_feedback')
def on_user_story_feedback(json):
    open_project.on_user_story_feedback(json, socketio)


@socketio.on('user_story_result')
def handle_user_story_done(json):
    open_project.handle_user_story_done(json)


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True, debug=False, port=5000)
