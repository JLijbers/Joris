from jira.client import JIRA


class JiraIntegration:
    def __init__(self, base_url, username, token, project):
        self.project = project
        self.client = JIRA(options={'server': base_url}, basic_auth=(username, token))

    def move_issue(self, issue_id, status):
        # Get the available transitions for the issue
        transitions = self.client.transitions(issue_id)

        # Find the transition ID for status
        in_progress_transition_id = None
        for transition in transitions:
            if transition['name'] == status:
                in_progress_transition_id = transition['id']
                break

        # If we found the transition ID, use it to transition the issue
        if in_progress_transition_id:
            self.client.transition_issue(issue_id, in_progress_transition_id)
        else:
            print(f"Could not find {status} transition for the JIRA issue.")

    def post_comment(self, issue_id, comment_text):
        # Add the comment to the issue
        self.client.add_comment(issue_id, comment_text)

