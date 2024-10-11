<img src="flask_app/static/img/logo.png" alt="Joris Logo" width="200"/>

# Joris: Automate User Story Implementation with AI

Joris is an application that revolutionizes the software development process by automatically implementing user stories. By leveraging AI, Joris transforms feature requests into code changes, making your development workflow more efficient and streamlined.

## Key Features

- **Automated User Story Implementation**: Input user stories and let Joris handle the rest—from refinement to code generation and integration.
- **AI-Powered Story Refinement**: Utilizes OpenAI models to enhance user stories, ensuring clarity and actionable outcomes.
- **Code Generation & Integration**: Automatically generates code based on refined user stories and seamlessly integrates it into your project.
- **Project Management**: Create and manage codebases for related user stories.
- **Version Control**: Built-in Git integration for managing commits and reviewing code changes.
- **API Integration**: Easy setup for OpenAI and Pinecone API keys to enable core AI functionalities.

## Prerequisites

- [Conda](https://docs.conda.io/en/latest/miniconda.html): For managing Python dependencies
- Python: Ensure it's available in your Conda environment
- Git: For version control and managing code changes
- [OpenAI API Key](https://openai.com/): For the AI-based functionalities
- [Pinecone API Key](https://www.pinecone.io/): For vector database integration

### Optional Prerequisites

For additional features, you need the following:

- **Run as desktop client** (instead of running in local browser):
  - [Node.js](https://nodejs.org/)

- **Jira Integration** (you will need a Jira project with the same name as your codebase/project):
  - Jira Base URL
  - Jira Username
  - Jira API Token

- **LangSmith Tracing**:
  - LangChain API Key
  - LangChain Project Name (tip: use same name as codebase/project)

These optional credentials can be configured in the setup page if you wish to use Jira integration for user story management and/or LangSmith for tracing the LLM API calls.


## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/joris.git
   cd joris
   ```

2. **Set Up the Conda Environment**:
   ```bash
   conda create -n joris-env python=3.10
   conda activate joris-env
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Install Node.js Dependencies**:
   ```bash
   npm install
   ```

## Usage

1. **Start the Application**:
   Run the Joris file (Only Windows = shortcut to the batch script) or use the following commands:
   ```bash
   conda activate joris-env
   npm start
   ```
   
   Or run the web-app directly using (in flask_app folder):
   ```bash
   conda activate joris-env
   python main.py
   ```

2. **Setup: Configure API Keys**:
   Start the application and navigate to the setup page to enter your OpenAI and Pinecone API keys.

3. **Create a New Project**:
   - Navigate to the "Create Project" section.
   - Input your project name and directory (directory of the codebase of the project).

4. **Open a Project**:
   - Open a project by selecting it in the dropdown section of 'Open Project'.

5. **Automatically Implement User Stories**:
   - Add a new user story by typing in the new-user-story field and pressing enter, or import them from Jira (use Jira-logo-button).
   - Drag-and-drop the user story to the 'play' button.
   - Joris will start working on the user story: it processes the codebase and creates a vectordb-index (if it is the first run for that project/codebase), and after that it starts refining the user-story (creating Acceptence Criteria for it).
   - The user is prompted for feedback on the Acceptence Criteria (to make sure Joris starts working on what is actually required)
   - Review the automatically generated code changes in the Git-repo, make changes if needed, and provide Joris feedback on the end-result.


## Starting a New Web Application (instead of using existing project)

To start a new web application from scratch:
1. Copy the `empty_example_application` folder to your desired location.
2. Rename the folder as needed.
3. Use this new directory as your project directory in Joris.


## To-Do List and Contributing

We're constantly working to improve Joris. Here are some items on our to-do list:

- [ ] Improve error handling
- [ ] Improve setup: allowing changing just one or a few fields, instead of overwriting all
- [ ] Remove hard-coded parts like setting LLM-model versions
- [ ] Test different embedding strategies
- [ ] Test use of graphRAG
- [ ] Let user choose which VectorDB to use (e.g. local)
- [ ] Let user choose which LLM to use (e.g. local)
- [ ] Functionality to add context to user-story (e.g. links to example code, icons, …)
- [ ] Feedback-loop on generated code changes
- [ ] Make use of unit tests
- [ ] Add option to delete codebases/projects
- [ ] Improve UI
- [ ] Improve (code) documentation
- [ ] Improve VectorDB integration (should probably not be in UserStory class)

We welcome contributions to these or new to-do's! Please follow these steps:

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](https://opensource.org/licenses/MIT) file for details.

## Contact

If you have any questions or need assistance, please [open an issue](https://github.com/JLijbers/joris/issues) or contact me.
