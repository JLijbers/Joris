import re
import os
import threading

from flask_socketio import SocketIO, emit

from . import prompts
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

socketio = SocketIO()
# Global state to track the refinement process for each user
global refinement_state
refinement_state = {}
feedback_received = threading.Event()


def summarize(content, models):
    # Initialize API call
    model = ChatOpenAI(temperature=0,
                       model_name=models['simple_task_model'],
                       request_timeout=120)
    prompt = PromptTemplate(template=prompts.summarize_prompt, input_variables=["content"])
    chain = prompt | model

    # Run
    summary = chain.invoke({"content": content})

    return summary.content


def describe_application(summary, folder_structure, models):
    print("Generating short description of the application..")

    # Initialize the API call
    model = ChatOpenAI(temperature=0,
                       model_name=models['simple_task_model'],
                       request_timeout=120,
                       top_p=0.1)
    prompt = PromptTemplate(template=prompts.description_prompt, input_variables=["summary", "folder_structure"])
    chain = prompt | model

    # Get result
    result = chain.invoke({"summary": summary, "folder_structure": folder_structure})

    return result.content


def relevant_code(original_story: str, updated_story: str, folder_structure: str, summary: str, models: dict) -> str:
    print("Determining which code files are relevant..")

    # Initialize API call
    model = ChatOpenAI(temperature=0,
                       model_name=models['simple_task_model'],
                       request_timeout=120,
                       max_tokens=100,
                       top_p=0.05)
    prompt = PromptTemplate(template=prompts.relevant_code_prompt, input_variables=["original_story",
                                                                                    "updated_story",
                                                                                    "folder_structure",
                                                                                    "summary"])
    chain = prompt | model

    # Run
    result = chain.invoke({"original_story": original_story,
                           "updated_story": updated_story,
                           "folder_structure": folder_structure,
                           "summary": summary})

    return result.content


def generate_instructions(vectordb, updated_story: str, code_needed: str, models: dict) -> str:
    print("Generating instructions..")
    code_str = vectordb.search_vectordb(code_needed)

    # Initialize API call
    model = ChatOpenAI(temperature=0,
                       model_name=models['hard_task_model'],
                       request_timeout=120,
                       stop="Step 6",
                       top_p=0.05)
    prompt = PromptTemplate(template=prompts.instructions_prompt, input_variables=["updated_story", "code_str"])
    chain = prompt | model

    # Run
    instructions = chain.invoke({"updated_story": updated_story, "code_str": code_str})

    return instructions.content


def generate_code(vectordb, instructions: str, updated_story: str, models: dict) -> str:
    print("Generating code changes based on instructions..")

    # Initialize API call
    model = ChatOpenAI(temperature=0,
                       model_name=models['hard_task_model'],
                       request_timeout=120,
                       top_p=0.05)
    prompt = PromptTemplate(template=prompts.code_prompt, input_variables=["updated_story", "instructions", "step",
                                                                           "code_str"])
    chain = prompt | model

    # Define remaining variables for input in prompt (other two are input in calling the function)
    instructions_split = re.split('\n\n', instructions.strip())
    track_list = ""

    # Loop over different steps in instructions and run agent for every step
    for i, step in enumerate(instructions_split):
        # Find part(s) of the code to use and update
        lines = step.strip().split('\n')
        file_line = lines[1]
        search_query = lines[2]
        file_path = file_line.split("File: ", 1)[-1]
        file_name = os.path.basename(file_path)

        if file_name:
            code_str = vectordb.retrieve_embeddings(search_query, k=1, file=file_name)
        else:
            code_str = vectordb.retrieve_embeddings(search_query, k=1)

        # Getting another possible relevant part of code based on instruction
        if len(lines) > 3:
            second_search_query = '\n'.join(lines[3:])
            vdb_two = vectordb.retrieve_embeddings(second_search_query, k=1)
            if vdb_two and vdb_two != code_str:
                code_str += vdb_two

        part_to_remove = "\n\n\n <ANOTHER POSSIBLY RELEVANT CODE CHUNK BELOW> \n\n\n"
        # Check if the code_str ends with the part_to_remove
        if code_str.endswith(part_to_remove):
            # Remove the part_to_remove from the end of code_str
            code_str = code_str[: -len(part_to_remove)]

        # Run agent
        result = chain.invoke({"updated_story": updated_story, "instructions": instructions,
                               "step": i + 1, "code_str": code_str})

        # Combine code changes from all steps
        track_list += result.content + "\n\n"

    # Sanity check generated code steps
    refine_prompt = PromptTemplate(template=prompts.refine_prompt, input_variables=["updated_story", "track_list"])
    refine_chain = refine_prompt | model

    print("Reviewing suggested code changes..")
    revised_result = refine_chain.invoke({"updated_story": updated_story, "track_list": track_list})
    print("Code changes are ready for review..")
    return revised_result.content


def refine_user_story(original_story, codebase_description, user_id, models):
    """
    Initiates the user-story refinement process.

    Parameters:
    original_story (str): The original user story description.
    codebase_description (str): A short description of the application's current state
    user_id (str): Unique identifier for the user's session.
    models (dict): Models used for processing.
    """
    # Initialize the refinement process
    refinement_state[user_id] = {
        "user_story": original_story,
        "feedback_iterations": 0,
        "models": models,
        "current_response": None
    }

    model = ChatOpenAI(temperature=0,
                       model_name=models['simple_task_model'],
                       request_timeout=120,
                       top_p=0.05)
    model_parser = model | StrOutputParser()
    first_prompt_template = PromptTemplate(template=prompts.acceptance_criteria_start, input_variables=["description",
                                                                                                        "user_story"])

    chain_1 = (
            first_prompt_template
            | model_parser
            | {"first_run_response": RunnablePassthrough()}
    )

    first_run_response_dict = chain_1.invoke({"description": codebase_description, "user_story": original_story})
    first_run_response = first_run_response_dict[next(iter(first_run_response_dict))]
    refinement_state[user_id]["current_response"] = first_run_response
    emit('script_output', {'data': f"To realize this user-story I will use these acceptance criteria: "
                                   f"\n\n{first_run_response}"})
    emit('script_output', {'data': "..."})
    emit('request_user_story_feedback', {'message': "Please respond whether you agree with this (yes/y), or provide "
                                                    "feedback to specify your wishes:"})
    feedback_received.wait()

    # Function resumes here - clean-up and return result
    result = refinement_state[user_id]["current_response"]
    split_result = result.split('riteria:\n')

    if len(split_result) > 1:
        cleaned_result = split_result[1]
    else:
        # Handle the case where 'riteria:\n' is not found in the string
        cleaned_result = split_result[0]

    del refinement_state[user_id]

    return cleaned_result


def refine_user_story_iteration(original_story, user_id, models, user_response):
    feedback_received.clear()

    model = ChatOpenAI(temperature=0,
                       model_name=models['simple_task_model'],
                       request_timeout=120,
                       top_p=0.05)
    model_parser = model | StrOutputParser()

    second_prompt_template = PromptTemplate(template=prompts.acceptance_criteria_iterate,
                                            input_variables=["user_story", "first_run_response", "user_response"])

    chain_2 = (
            second_prompt_template
            | model_parser
            | {"second_run_response": RunnablePassthrough()}
    )

    second_run_response_dict = chain_2.invoke({
        "user_story": original_story,
        "first_run_response": refinement_state[user_id]["current_response"],
        "user_response": user_response
    })

    second_run_response = second_run_response_dict[next(iter(second_run_response_dict))]
    refinement_state[user_id]["current_response"] = second_run_response
    refinement_state[user_id]["feedback_iterations"] += 1
    emit('script_output', {'data': f"After considering your feedback, I revised the acceptance criteria like "
                                   f"this:\n\n{second_run_response}"})
    emit('request_user_story_feedback', {'message': "Please respond whether you agree with this (yes/y), or provide "
                                                    "feedback to specify your wishes:"})


def finalize_feedback():
    feedback_received.set()
