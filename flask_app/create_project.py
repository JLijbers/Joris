from flask import Blueprint, render_template, current_app
from codebase.codebase_class import Codebase

create_project_bp = Blueprint('create_project', __name__)


@create_project_bp.route('/create-project')
def create_project():
    user_id = '12345'  # Retrieve user_id as needed
    return render_template('CreateProjectPage.html', user_id=user_id)


def handle_create_project(json, socketio):
    project_name = json['project_name']
    directory = json['directory']

    # Create a new codebase instance
    new_codebase = Codebase(name=project_name, directory=directory)

    # Write to database
    with current_app.db_manager.session_scope() as session:
        # Add codebase to the database
        current_app.db_manager.add_or_update_codebase(session, new_codebase)

    # Emit a response back to the client
    socketio.emit('project_saved', {'message': f'Project {project_name} created successfully'})
