import configparser
from flask import Blueprint, render_template
from config import CONFIG_PATH

setup_bp = Blueprint('setup', __name__)


@setup_bp.route('/setup')
def setup():
    user_id = '12345'  # Retrieve user_id as needed
    return render_template('SetupPage.html', user_id=user_id)


def handle_save_settings(json, socketio):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'OPENAI_API_KEY': json['openai_api_key'],
        'PINECONE_API_KEY': json['pinecone_api_key'],
        'JIRA_BASE_URL': json.get('jira_base_url', ''),
        'JIRA_USERNAME': json.get('jira_username', ''),
        'JIRA_TOKEN': json.get('jira_token', ''),
        'LANGCHAIN_API_KEY': json.get('langchain_api_key', ''),
        'LANGCHAIN_PROJECT': json.get('langchain_project', '')
    }

    # Set Langchain tracing to true if API key is provided
    if json.get('langchain_api_key'):
        config['DEFAULT']['LANGCHAIN_TRACING_V2'] = 'true'
    else:
        config['DEFAULT']['LANGCHAIN_TRACING_V2'] = 'false'

    with open(CONFIG_PATH, 'w') as config_file:
        config.write(config_file)

    # Emit a response back to the client
    socketio.emit('settings_saved', {'message': 'Configuration saved successfully'})
