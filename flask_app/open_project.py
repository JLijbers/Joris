import os
import json
import time
import threading
import configparser
from flask import Blueprint, render_template, session, request, current_app

from config import CONFIG_PATH

from userstory.userstory_class import UserStory

from utils.jira_integration import JiraIntegration
from utils.vectordb_integration import VectorDBIntegration
from utils.git_manager import finalize_git_feedback
from utils.code_change_handler import implement_code_changes

from llm.llm_calls import refinement_state, refine_user_story_iteration, finalize_feedback

###############
# Set webpage #
###############

user_story_done = None
refined_user_story = None
user_story_done_feedback = threading.Event()
open_project_bp = Blueprint('open_project', __name__)


@open_project_bp.route('/open-project')
def open_project():
    user_id = session.get('username', 'default_user')
    project_name = request.args.get('name', '')

    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)

    # Get models
    default_models = {'simple_task_model': "gpt-4o-mini", 'hard_task_model': "gpt-4o"}
    models_config_str = config['DEFAULT'].get('models', json.dumps(default_models))
    models_config = json.loads(models_config_str)
    os.environ["models"] = json.dumps(models_config)

    # Set API keys
    os.environ["OPENAI_API_KEY"] = config['DEFAULT']['OPENAI_API_KEY']
    os.environ["PINECONE_API_KEY"] = config['DEFAULT']['PINECONE_API_KEY']

    # Set Jira credentials
    os.environ["jira_base_url"] = config['DEFAULT'].get('JIRA_URL', '')
    os.environ["jira_username"] = config['DEFAULT'].get('JIRA_USERNAME', '')
    os.environ["jira_password"] = config['DEFAULT'].get('JIRA_PASSWORD', '')

    # Set LangSmith-environment
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = config['DEFAULT'].get('LANGCHAIN_API_KEY', '')
    os.environ["LANGCHAIN_TRACING_V2"] = config['DEFAULT'].get('LANGCHAIN_TRACING_V2', 'false')
    os.environ["LANGCHAIN_PROJECT"] = config['DEFAULT'].get('LANGCHAIN_PROJECT', '')

    # Get project configurations
    with current_app.db_manager.session_scope() as db_session:
        # Fetch the codebase from the database
        codebase = current_app.db_manager.get_codebase(db_session, project_name)

        # Get user stories that still need processing
        user_stories = db_session.query(
            UserStory.original_story,
            UserStory.jira_id
        ).filter(
            UserStory.codebase_id == codebase.id,
            UserStory.status.notin_(['implemented_manual_changes', 'implemented_successfully'])
        ).all()

    user_stories = [dict(text=story[0], jira_id=story[1]) for story in user_stories]

    return render_template('OpenProjectPage.html',
                           user_id=user_id,
                           project_name=project_name,
                           user_stories=user_stories)


####################################################
# Run user-story // Main application functionality #
####################################################

def handle_run_story(json_data, socketio):
    socketio.emit('script_output', {'data': "Started working on provided user-story.."})

    user_id = json_data['user_id']
    project_name = json_data['project_name']
    jira_id = json_data['jira_id']
    current_user_story = json_data['user_story'].strip()
    models_str = os.environ["models"]
    models = json.loads(models_str)

    ################################################################
    # Setup connections to jira, git, database and vector database #
    ################################################################

    # Set JIRA integration if any
    if jira_id != '':
        jira = JiraIntegration(base_url=os.environ["jira_base_url"],
                               username=os.environ["jira_username"],
                               token=os.environ["jira_password"],
                               project=project_name)
        jira.move_issue(jira_id, status="In Progress")
    else:
        jira = None

    # Database connection
    with current_app.db_manager.session_scope() as current_session:
        # Get codebase from database
        codebase = current_app.db_manager.get_codebase(current_session, project_name)

        # Check if git repository it is ready for code changes (has no pending changes)
        current_app.git_manager.set_directory(codebase.directory)
        current_app.git_manager.handle_dirty_repo()

        # Create a summary if it doesn't exist in db
        if not codebase.summary:
            socketio.emit('script_output', {'data': "Generating codebase summary.."})
            codebase.generate_summary(models)
            codebase.describe_application(models)
            current_app.db_manager.add_or_update_codebase(current_session, codebase)

        # Get or create VectorDB instance
        vectordb = VectorDBIntegration(vectordb_api_key=os.getenv("PINECONE_API_KEY"), index_name=project_name)

        if not vectordb.index_exists():
            socketio.emit('script_output', {'data': "Creating new vector database index.."})
            # Create a new index if it doesn't exist
            vectordb.create_index()

        if not vectordb.is_index_populated():
            socketio.emit('script_output', {'data': "Embedding and storing codebase to new index.."})
            # Embed and store codebase-directory if index is empty
            vectordb.embed_and_store(directory=codebase.directory)

        ###############################
        # Start processing user-story #
        ###############################

        # Get UserStory instance from db
        user_story = current_app.db_manager.get_user_story(current_session, codebase.name, current_user_story)
        user_story.vectordb = vectordb

        # Refine user-story
        if user_story.refined_story is None:
            user_story.refine_user_story(codebase.description, user_id, models)

        # Set global-variable for later use
        global refined_user_story
        refined_user_story = user_story.refined_story

        # Define which code files are relevant using the summary of the current codebase
        socketio.emit('script_output', {'data': "Determining which code files are relevant.."})
        if user_story.relevant_files is None:
            user_story.relevant_code(codebase.folder_structure, codebase.summary, models)
            current_app.db_manager.update_user_story(current_session, user_story)
            if jira_id != '':
                jira.post_comment(jira_id, f"These files seem relevant: \n{user_story.relevant_files}")

        # Generate instructions for implementing the functionality, using code from the relevant files
        socketio.emit('script_output', {'data': "Generating instructions.."})
        if user_story.instructions is None:
            user_story.generate_instructions(models)
            current_app.db_manager.update_user_story(current_session, user_story)
            if jira_id != '':
                jira.post_comment(jira_id, f"Instructions: \n{user_story.instructions}")

        # Generate code changes based on the instructions and relevant code, function also reviews the suggested changes
        socketio.emit('script_output', {'data': "Generating code changes based on instructions.."})
        if user_story.generated_code is None:
            user_story.generate_code(models)
            current_app.db_manager.update_user_story(current_session, user_story)
            if jira_id != '':
                jira.post_comment(jira_id, f"Generated Code: \n{user_story.generated_code}")

        # Implement suggested code changes
        implement_code_changes(generated_code=user_story.generated_code, socketio=socketio)

        # Set the commit message
        current_app.git_manager.set_commit_message(summary="JORIS - automatically implemented user-story",
                                                   description=user_story.original_story)
        current_app.git_manager.stage_changes()

        # Let user know and wait for feedback
        socketio.emit('script_output', {'data': 'Done processing the user-story..'})
        socketio.emit('script_output', {'data': "Please review the suggested code changes in the prepared GIT commit.."})
        socketio.emit('user_story_done', {'data': "Let me know how it worked out.."})
        user_story_done_feedback.wait()

        if user_story_done != 'implementation_failed':
            # Empty existing vectordb-index and refill with renewed codebase
            socketio.emit('script_output', {'data': 'Updating index in vector database..'})
            vectordb.flush_index()
            vectordb.embed_and_store(directory=codebase.directory)

            # Update database with new codebase summary, new description and realized user story
            socketio.emit('script_output', {'data': 'Updating codebase summary..'})
            codebase.update_summary(models)
            codebase.describe_application(models)
            current_app.db_manager.add_or_update_codebase(current_session, codebase)

            if jira_id != '':
                jira.move_issue(jira_id, status="Done")

            if user_story_done == "implemented_successfully":
                user_story.status = "implemented_successfully"
            else:
                user_story.status = "implemented_manual_changes"

            socketio.emit('script_output', {'data': 'All done! You can now start running a new user story.'})
        else:
            user_story.status = "implementation_failed"
            socketio.emit('script_output', {'data': 'That is too bad! You can try improving the user story (e.g. make '
                                                    'it a smaller functionality) and running it again. Or try running '
                                                    'another user story.'})
            # Possible future functionality: let user describe what was wrong and save failure-table in database

        current_app.db_manager.update_user_story(current_session, user_story)

    socketio.emit('enable_drop_object')
    current_app.git_manager.remove_msg_hook()
    print("Done running user story.")


#######################################
# Other client-side invoked functions #
#######################################

def handle_add_user_story(json_data):
    user_story_text = json_data['story']
    project_name = json_data['projectName']
    jira_id = json_data['jiraID']

    user_story = UserStory(jira_id=jira_id, vectordb=None, original_story=user_story_text)

    with current_app.db_manager.session_scope() as session:
        # Add user_story to database
        current_app.db_manager.add_user_story(session, project_name, user_story)


def handle_delete_user_story(json_data):
    user_story_text = json_data['user_story'].strip()
    project_name = json_data['projectName']

    with current_app.db_manager.session_scope() as session:
        # Get the associated codebase
        codebase = current_app.db_manager.get_codebase(session, project_name)

        # Find and delete the user story
        user_story = session.query(UserStory).filter(
            UserStory.codebase_id == codebase.id,
            UserStory.original_story == user_story_text
        ).one_or_none()

        if user_story:
            session.delete(user_story)


def import_jira_issues(json_data, socketio):
    project_name = json_data['project_name']

    with current_app.db_manager.session_scope() as session:
        # Get the associated codebase
        codebase = current_app.db_manager.get_codebase(session, project_name)

        # Extract unique jira_id's from existing user stories
        existing_jira_ids = {story.jira_id for story in codebase.user_stories if story.jira_id}

    try:
        jira = JiraIntegration(base_url=os.environ["jira_base_url"],
                               username=os.environ["jira_username"],
                               token=os.environ["jira_password"],
                               project=json_data['project_name'])

        jql = f"project = {jira.project} AND status = 'To Do' ORDER BY created DESC"

        # Search issues using search query
        data_list = jira.client.search_issues(jql)

        # If a new issue is spotted, extract the information and add it to the database
        if data_list:
            with current_app.db_manager.session_scope() as session:
                for data in data_list:
                    if data.id not in existing_jira_ids:
                        new_user_story = UserStory(jira_id=data.id, vectordb=None,
                                                   original_story=data.fields.summary)
                        new_user_story.codebase = codebase
                        session.add(new_user_story)
                        socketio.emit('add_jira_story', {'jira_id': data.id, 'summary': data.fields.summary})
    except Exception as e:
        socketio.emit('script_output', {'data': f'Error importing Jira-issues: {e}. '
                                                f'Please check if credentials are in config-file.'})


def on_git_feedback_dirty(json_data, socketio):
    from flask import current_app
    feedback = json_data['feedback']

    if feedback == 'Commit Changes':
        current_app.git_manager.commit_changes()
        socketio.emit('script_output', {'data': 'Changes have been committed.'})
    elif feedback == 'Discard Changes':
        current_app.git_manager.discard_changes()
        socketio.emit('script_output', {'data': 'Changes have been discarded.'})
    elif feedback == 'Wait for Clean Repository':
        socketio.emit('script_output', {'data': 'Please handle the changes manually.'})
        while current_app.git_manager.is_dirty():
            socketio.emit('script_output', {'data': 'Waiting for the repository to be clean...'})
            time.sleep(10)
        socketio.emit('script_output', {'data': 'Repository is clean, continuing...'})

    finalize_git_feedback()


def on_user_story_feedback(json_data, socketio):
    user_id = json_data['user_id']
    feedback = json_data['feedback']

    state = refinement_state[user_id]
    feedback_iterations = state["feedback_iterations"]

    if feedback.lower() in ['yes', 'y', 'yeah', 'yep']:
        socketio.emit('script_output', {'data': "Great! I will start working on this."})
        finalize_feedback()
    else:
        feedback_iterations += 1
        if feedback_iterations < 3:
            refine_user_story_iteration(state["user_story"], user_id, state["models"], feedback)
        else:
            socketio.emit('script_output', {'data': "Reached the maximum of 3 user-story refinements. Will start "
                                                    "developing."})
            finalize_feedback()


def handle_user_story_done(json_data):
    global user_story_done, user_story_done_feedback
    user_story_done = json_data['feedback']
    user_story_done_feedback.set()
