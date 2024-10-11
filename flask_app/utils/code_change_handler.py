import re
import os


def implement_code_changes(generated_code, socketio):
    try:
        # Split instructions and generated_code into steps
        generated_code_steps = generated_code.split('Step ')
    except Exception as e:
        error_message = f"Generated code has invalid format: {str(e)}. No changes are implemented."
        print(error_message)
        socketio.emit('script_output', {'data': error_message})
        return

    # Apply changes per step
    for step, code_chunk in enumerate(generated_code_steps[1:], start=1):
        # Extract file path
        file_path = code_chunk.split('\n')[1].strip()

        if not os.path.exists(file_path):
            base_name = os.path.basename(file_path)
            message = f"File: {base_name} mentioned in step {step} does not exist. Creating new file."
            print(message)
            socketio.emit('script_output', {'data': message})
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            open(file_path, 'w').close()

        # Read the entire file content
        with open(file_path, 'r') as f:
            file_content = f.read()

        # Create a list of lines, splitting by newline
        file_lines = file_content.splitlines(keepends=True)

        # Extract original and updated code from generated_code
        try:
            code_parts = re.split(r'<<<<<<< ORIGINAL|=======|>>>>>>> UPDATED', code_chunk)
            assert len(code_parts) >= 3, "Invalid code part split"
            original, updated = code_parts[1:3]
        except Exception as e:
            message = f"Invalid format in generated code for step {step}: {str(e)}. Skipping this step."
            print(message)
            socketio.emit('script_output', {'data': message})
            continue

        # Clean-up original and updated
        original_lines = original.splitlines(keepends=True)
        updated_lines = updated.splitlines(keepends=True)
        if original_lines and original_lines[0].strip() == '':
            original_lines = original_lines[1:]
        if updated_lines and updated_lines[0].strip() == '':
            updated_lines = updated_lines[1:]

        # If new file was created add code to this new file
        if not file_content:
            with open(file_path, 'w') as file:
                file.writelines(updated_lines)
            continue

        # Check if this is an end-of-file insertion
        if not original.strip():
            # Append the updated content to the end of the file
            after_lines = file_lines + updated_lines
        else:
            try:
                # Find the index where the original content starts
                start_index = file_content.index(original.lstrip())

                # Determine line indices from character indices
                start_line_index = file_content.count('\n', 0, start_index)
                end_line_index = start_line_index + len(original_lines) - 1

                # Create new version of the file
                after_lines = file_lines[:start_line_index] + updated_lines + file_lines[end_line_index + 1:]

            except ValueError:
                # If 'original' is not found, append 'updated' to the end of the file
                after_lines = file_lines + updated_lines
                message = f"Original part of step {step} not found. Applying changes to end of file."
                print(message)
                socketio.emit('script_output', {'data': message})

        # Apply changes
        with open(file_path, 'w') as file:
            file.writelines(after_lines)

    return
