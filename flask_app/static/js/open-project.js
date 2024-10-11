// open-project.js
document.addEventListener('DOMContentLoaded', (event) => {
    // Get user_id and project_name from data attributes or a global object
    let user_id = document.body.dataset.userId;
    let project_name = document.body.dataset.projectName;

    // Set constants
    const socket = io('http://localhost:5000');
    const backlog = document.getElementById('backlog');
    const running = document.getElementById('running');
    const draggableContainer = document.getElementById('draggable-container');
    const trashButton = document.getElementById('trash-button');
    const outputDiv = document.getElementById('pythonOutput');

    // Socket event listeners
    initializeSocketEvents();

    // Initialize drag and drop
    let storyCount = document.querySelectorAll('#backlog div[draggable="true"]').length;
    let isDropAllowed = true;
    initializeDragAndDrop();

    // Initialize new user story input field
    initializeUserStoryInput()

    // Handle jira-button click
    document.getElementById('jira-button').onclick = () => socket.emit('jira_import', { project_name: project_name });

    // Functions
    function initializeDragAndDrop() {
        draggableContainer.addEventListener('dragover', handleDragOver);
        draggableContainer.addEventListener('dragleave', handleDragLeave);
        draggableContainer.addEventListener('drop', handleDrop);

        makeBacklogItemsDraggable();

        // Trash button events
        if (trashButton) {
            trashButton.addEventListener('dragover', handleTrashDragOver);
            trashButton.addEventListener('dragleave', handleTrashDragLeave);
            trashButton.addEventListener('drop', handleTrashDrop);
        } else {
            console.warn('Trash button not found in the DOM');
        }
    }

    function handleDragOver(event) {
        event.preventDefault();
        draggableContainer.classList.add('bg-gray-600');
    }

    function handleDragLeave() {
        draggableContainer.classList.remove('bg-gray-600');
    }

    function handleDrop(event) {
        event.preventDefault();
        draggableContainer.classList.remove('bg-gray-600');
        const data = event.dataTransfer.getData("Text");
        const jira_id = event.dataTransfer.getData("JiraID");

        running.innerHTML = '';
        running.appendChild(outputDiv);

        socket.emit('run_story', { user_id, project_name, jira_id: jira_id, user_story: data});
    }

    function makeBacklogItemsDraggable() {
        backlog.querySelectorAll('div[draggable="true"]').forEach((item) => {
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragend', handleDragEnd);
        });
    }

    function handleDragStart(event) {
        event.dataTransfer.setData("Text", event.target.textContent);
        event.dataTransfer.setData("JiraID", event.target.getAttribute('data-jira-id'));
        event.target.classList.add('opacity-50');
    }

    function handleDragEnd(event) {
        event.target.classList.remove('opacity-50');
    }

    function handleTrashDragOver(event) {
        event.preventDefault();
        trashButton.classList.add('bg-red-600');
    }

    function handleTrashDragLeave() {
        trashButton.classList.remove('bg-red-600');
    }

    function handleTrashDrop(event) {
        event.preventDefault();
        const data = event.dataTransfer.getData("Text");
        trashButton.classList.remove('bg-red-600');
        socket.emit('delete_user_story', { user_story: data, projectName: project_name });

        removeStoryFromDOM(data);
    }

    function removeStoryFromDOM(storyText) {
        const storyElements = backlog.querySelectorAll('div');
        storyElements.forEach(element => {
            if (element.textContent.trim() === storyText.trim()) {
                element.remove();
            }
        });
    }

    function initializeUserStoryInput() {
        const newUserStoryInput = document.getElementById('newUserStory');
        newUserStoryInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                let newUserStory = event.target.value.trim();
                let jiraID = ''
                if (newUserStory !== '') {
                    addNewUserStory(newUserStory, jiraID);
                    event.target.value = '';
                } else {
                    alert("Please enter a user story.");
                }
            }
        });
    }

    function addNewUserStory(storyText, jiraID) {
        storyCount++;
        const newStoryDiv = createStoryElement(storyText, storyCount, jiraID);
        backlog.appendChild(newStoryDiv);

        socket.emit('add_user_story', { story: storyText, projectName: project_name, jiraID: jiraID });
    }

    function createStoryElement(text, id, jiraID) {
        const div = document.createElement('div');
        div.id = 'story' + id;
        div.setAttribute('data-jira-id', jiraID);
        div.className = 'bg-gray-700 p-2 rounded';
        div.setAttribute('draggable', 'true');
        div.textContent = text;
        div.addEventListener('dragstart', handleDragStart);
        div.addEventListener('dragend', handleDragEnd);
        return div;
    }

    // Function to redirect socket events to the right function
    function initializeSocketEvents() {
        socket.on('enable_drop_object', () => { isDropAllowed = true; });
        socket.on('request_git_feedback_dirty', handleGitFeedbackDirty);
        socket.on('request_user_story_feedback', handleUserStoryRefinementFeedback);
        socket.on('user_story_done', handleUserStoryDone);
        socket.on('add_jira_story', (data) => { addNewUserStory(data.summary, data.jira_id) });
        socket.on('script_output', (data) => {
            let formattedText = formatText(data.data);
            outputDiv.innerHTML += `<div>${formattedText}</div>`;
        });
    }

    // Function for formatting script output text
    function formatText(text) {
        // Convert newlines to <br>
        text = text.replace(/\n/g, '<br>');
        // Convert **bold** to <strong>bold</strong>
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Convert numbered items to list items
        text = text.replace(/(\d+)\.\s(.*?)(?=\d\.|$)/g, '<li>$2</li>');
        // Wrap the list items with <ol>
        text = text.replace(/(<li>.*<\/li>)/g, '<ol>$1</ol>');
        return text;
    }

    // Function for handling dirty git repo
    function handleGitFeedbackDirty(data) {
        const gitFeedbackButtons = document.getElementById('gitFeedbackButtons');

        if (outputDiv && gitFeedbackButtons) {
            outputDiv.innerHTML += `<div>${data.message}</div>`;
            gitFeedbackButtons.style.display = 'block';  // Show the buttons

            document.getElementById('commitChanges').onclick = () => handleGitFeedback('Commit Changes');
            document.getElementById('discardChanges').onclick = () => handleGitFeedback('Discard Changes');
            document.getElementById('waitForClean').onclick = () => handleGitFeedback('Wait for Clean Repository');
        }
    }

    function handleGitFeedback(feedback) {
        socket.emit('git_feedback_dirty', { feedback: feedback });
        document.getElementById('gitFeedbackButtons').style.display = 'none';  // Hide the buttons after feedback
    }

    // Function for getting acceptance criteria feedback
    function handleUserStoryRefinementFeedback(data) {
        const userStoryRefinementFeedback = document.getElementById('userStoryRefinementFeedback');

        if (outputDiv && userStoryRefinementFeedback) {
            outputDiv.innerHTML += `<div>${data.message}</div>`;
            userStoryRefinementFeedback.style.display = 'block';  // Show the input field

            document.getElementById('sendFeedback').onclick = () => {
                let feedback = document.getElementById('feedbackInput').value;
                if (feedback.trim() !== '') {
                    socket.emit('user_story_feedback', { user_id: user_id, feedback: feedback });
                    document.getElementById('feedbackInput').value = '';  // Clear the input
                    userStoryRefinementFeedback.style.display = 'none';  // Hide the input and button
                } else {
                    alert("Please enter some feedback.");
                }
            };
        }
    }

    // Function for handling feedback on finished user story
    function handleUserStoryDone(data) {
        const userStoryResultFeedback = document.getElementById('userStoryResultFeedback');

        if (outputDiv && userStoryResultFeedback) {
            outputDiv.innerHTML += `<div>${data.message}</div>`;
            userStoryResultFeedback.style.display = 'block';  // Show the buttons

            document.getElementById('userstorySuccess').onclick = () => handleUserStoryResultFeedback('implemented_successfully');
            document.getElementById('userstoryManual').onclick = () => handleUserStoryResultFeedback('implemented_manual_changes');
            document.getElementById('userstoryFailed').onclick = () => handleUserStoryResultFeedback('implementation_failed');
        }
    }

    function handleUserStoryResultFeedback(feedback) {
        socket.emit('user_story_result', { feedback: feedback });
        document.getElementById('userStoryResultFeedback').style.display = 'none';  // Hide the buttons after feedback
    }
});