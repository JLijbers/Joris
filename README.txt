1) Create virtual environment and install requirements from requirements.txt
2) Run main.py inside that virtual environment

If you want to start from scratch creating a new web application (instead of continuing with an existing one):
You can cut and paste the 'empty_example_application' folder to your desired location, adjust the name,
and use that as your new project directory.

p.s. If you want LangSmith-tracing add these variables to the config.ini (which is created after Setup):
langchain_api_key = your_langchain_api_key
langchain_project = your_langsmith_project_name
langchain_tracing_v2 = true