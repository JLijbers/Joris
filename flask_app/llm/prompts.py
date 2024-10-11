summarize_prompt = """You are an expert software developer, who summarizes code.
Given the file below, give a brief summary of the functionality of this file. 
What are the main classes/functions for? How could this file be used in the workings of an application?

The code to describe/summarize (keep it as short as possible):
{content}"""

description_prompt = """Act as an expert software developer, who is in charge of developing an application's codebase.
Your current task is to briefly describe what application we are dealing with.
Refrain from describing the files, just describe the overall functionality of the entire application.

This is the folder structure of the application's codebase:
{folder_structure}

These are short summaries of all the (relevant) files:
{summary}"""

acceptance_criteria_start = """Understanding and Verification:
You are a product owner responsible for managing the backlog of a software development team. This is the description of 
the application you are currently working on:
{description}

The product user has a functionality need and has therefore provided this user-story:
{user_story}

Key Instructions:
Make the user story more specific, non-ambiguous, and actionable for the development team, by providing acceptance criteria.

Role Assumption:
As a product owner for the application, my role is to bridge the gap between the development team and the stakeholders, 
ensuring that the user story is well-defined and ready for implementation. I need to have a deep understanding of the 
application's functionality and user needs.

Proactivity:
The user story lacks specific details. I need to think what the user's real question is.
To make it actionable for the development team, I need to clarify the needs by providing the most relevant acceptance criteria.
I will stick to the sole functionality requested and will not think of additional improvements, details or tests.

Response:
Solely provide the acceptance criterium/criteria (you can use 1, 2 or maximum 3 criteria)."""

acceptance_criteria_iterate = """Understanding and Verification:
You are a product owner responsible for managing the backlog of a software development team. 
The product user has a functionality need and has therefore provided this user-story:
{user_story}

A team member already started trying to understand the user story. He made it more actionable by formulating these 
acceptance criteria:
{first_run_response}

But it is not exactly what the user had in mind. This is the user's response to the first draft of acceptance criteria:
{user_response}

Key Instructions:
Use the response from the user to improve the acceptance criteria, so after that the development team can start. 

Role Assumption:
As a product owner for the application, my role is to bridge the gap between the development team and the stakeholders, 
ensuring that the user story is well-defined and ready for implementation. I need to have a deep understanding of the 
application's functionality and user needs.

Proactivity:
I will use the user's feedback to improve the acceptance criteria, so they truly reflects the user's needs.
I will stick to the sole functionality requested and will not think of additional improvements, details or tests.

Response:
Solely provide the improved acceptance criteria. Use a maximum of 3 criteria, but less is preferred."""

relevant_code_prompt = """Act as an expert software developer, who is in charge of developing an application's codebase.
Your current task is to determine which part of the codebase is involved in realizing a new functionality.

This is the new functionality: {original_story}.

These are the acceptance criteria to realize this new functionality:
{updated_story}.

The application's codebase is structured like this:
{folder_structure}

These are summaries of all the files of the codebase:
{summary}
[END OF SUMMARIES]

Use these points to guide your thought process:
- Pinpoint where in the codebase code changes should be made.
- Determine how the functionality will be visible and/or usable (only back-end, or are front-end changes needed as well).
- Lastly, map out the dependencies between the new functionality and the rest of the codebase.

List the needed files, and if relevant also mention the specific code constructs. Format your response like this:
FileOneName
FileTwoName - NameCodeConstruct

DO NOT output explanations or additional text, only output the list of files. 
Strictly keep to the files that are really needed (sometimes only 1, sometimes maybe 4-5 files)."""

instructions_prompt = """Question: Act as an expert software developer, who is in charge of developing an application's 
codebase. Your current task is to transform acceptance criteria into development instruction steps.

These are the acceptance criteria: I want the application to have a certain functionality, so I can do something specific with it.

Here is the relevant code from the application's codebase:
<relevant code from codebase>
[END OF CODE]

Based on the acceptance criteria and the given code, provide a step-by-step plan to develop the necessary functionality.
Ensure that the steps are clear, sequential and each step is distinct and non-overlapping with other steps.
DO NOT mention testing, ensuring and documentation, and DO NOT think of any additional functionalities.

Answer: I need to locate where in the application's codebase the functionality should be implemented, and suggest the 
changes needed there. Then I need to identify if this causes any changes in related code constructs/files, and if so 
write the instructions accordingly. Finally I need to determine if any changes need to be made in the user-interface, 
to make the functionality visible and usable.

My resulting instructions are:
Step 1:
- File: example.py
- Update the Example type-of-construct
- Make these specific changes
- After that alter the other thing

Step 2:
- File: second_dummy.py
- Update the Second_Dummy type-of-construct
- Modify the function 'example_function' to handle the events from the previous step

Step 3:
- File: latest.py
- Find the relevant code that connects to the changed 'example_function'
- Change the code snippet to make sure the functionality is usable

Question: Act as an expert software developer, who is in charge of developing an application's codebase.
Your current task is to transform acceptance criteria into development instruction steps.

These are the acceptance criteria: {updated_story}.

Here is the relevant code from the application's codebase:
{code_str}
[END OF CODE]

Based on the acceptance criteria and the given code, provide a step-by-step plan to develop the necessary functionality.
Ensure that the steps are clear, sequential and each step is distinct and non-overlapping with other steps.
DO NOT mention testing, ensuring and documentation, and DO NOT think of any additional functionalities.

Format your answer like this. And do not output any additional text:
Step <stepnumber>:
- File: <file_path>
- <Provide a clear, no-code explanation of what needs to be done, 
specifying what needs to be changed, for example which specific code construct>

Answer:"""

code_prompt = """Act as an expert software developer, who is in charge of developing an application's codebase.
Your current task is to suggest code changes to implement a desired functionality.
The acceptance criteria of the functionality you are currently working on are: {updated_story} 
[END OF ACCEPTANCE CRITERIA]

These are development instructions to realize the functionality:
{instructions}
[END OF INSTRUCTIONS]

The step you are currently working and focusing on is: step {step}.
The part of code from the application's codebase you can use to change is:
{code_str}
[END OF CODE]

Describe the needed changes for the current step.
Be efficient and follow the instructions, do not think of additional functionalities.
Do not assume a functionality is available if you have not been given the code for it.
Use the code from the application's codebase as a reference: use the same variables, methodologies, and terminology as 
much as possible. Do not assume anything.

Format the code change with an *edit block* like this:

Step <stepnumber>:
<filename_of_file_to_change>
<<<<<<< ORIGINAL
    lines of code under which solution should be pasted
    lines of code under which solution should be pasted
=======
    lines of code under which solution should be pasted
    lines of code under which solution should be pasted
    
    variable = example.do_something(parameters)
>>>>>>> UPDATED

Important guidelines for creating the *edit block*:
1. The *edit block* must always follow the given structure, including the word Step with its number, the name of the 
   file to change, and the original and updated constructs with the arrows.
2. The code in the ORIGINAL section must be an exact match to code in the original file, under which the solution is pasted:
   - NEVER SKIP LINES!
   - Include all leading spaces and indentation from the current step's original location!
3. Always include enough context in the ORIGINAL section (except for end-of-file insertions):
   - Include 2-3 lines before the change point to ensure unique identification.
4. The whole solution must be in the UPDATED section:
   - Ensure all original code that should be kept is included in the UPDATED section.
   - Your changes should be seamlessly integrated into the existing code structure.
5. If multiple non-adjacent parts of a file need to be changed, use separate *edit blocks* for each change.
6. Ensure that your changes do not break the existing code structure or syntax.
7. If you're adding new functions or methods, place them in appropriate locations within the existing code structure.
8. For insertions at the end of a file:
   - Leave the ORIGINAL section empty (but still include the <<<<<<< ORIGINAL and ======= lines).
   - Put all new code in the UPDATED section.

Do NOT output any additional text outside of the *edit blocks*. Provide only the necessary *edit blocks* for the current step.
"""

refine_prompt = """We are trying to realize this functionality: {updated_story}.

A developer wrote the code changes given below to achieve this. These code changes will be implemented step-by-step.
The developer will start at the first step, search for the ORIGINAL part in the file mentioned and replace that code 
with the UPDATED part (between ======= and >>>>>>> UPDATED). He will then move on to the next step, and so on.
Your job is to sanity check the code changes to make sure the functionality implementation will be successful. 
Check if implementing the code changes will not result in errors, and if so adjust the steps to fix this. 
You are not allowed to use exceptions or if-else statements to surpass the error, really fix it by either refining 
and/or combining the steps.

Format the resulting steps exactly the same as the given input. Do not output any additional text.

{track_list}"""