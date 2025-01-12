import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)

def generate_test_with_ai(main_code: str, dependency_code: list[str]):
    formatted_dependencies = "\n\n".join(
        f"Dependency Code {i+1}:\n{dep}" for i, dep in enumerate(dependency_code)
    )

    prompt = f"""
    The following is the main code that requires unit tests:

    Main Code:
    {main_code}

    The main code depends on the following dependency code(s). Inspect these as they may influence the
    behavior of the main code and require their own unit tests:

    {formatted_dependencies}

    Your task:
    1. Generate unit tests for the main code.
    2. If the dependencies include any functions or logic that influence the main code, 
    generate unit tests for those dependencies as well.
    3. Ensure the test cases cover edge cases, typical usage, and error scenarios.

    Provide the test cases in a Python-compatible format, using `unittest` or `pytest`.
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    return chat_completion.choices[0].message.content


def generate_with_file():
    global all_messages
    my_file = client.files.create(
        file=Path("uploads/d.py/d.py"),
        purpose="assistants",
    )

    my_assistant = client.beta.assistants.create(
        model="gpt-4o",
        instructions="You are a file analyze chatbot. Use your knowledge base to best respond to file uploads.",
        name="File Analyze Chatbot",
        tools=[{"type": "file_search"}]
    )

    my_thread = client.beta.threads.create()

    my_thread_message = client.beta.threads.messages.create(
        thread_id=my_thread.id,
        role="user",
        content="Generate a unit test file for the uploaded file.",
        attachments=[{'file_id': my_file.id, 'tools': [{'type': 'file_search'}]}]
    )

    my_run = client.beta.threads.runs.create(
        thread_id=my_thread.id,
        assistant_id=my_assistant.id
    )
    print(f"This is the run object: {my_run} \n")

    while my_run.status in ["queued", "in_progress"]:
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=my_thread.id,
            run_id=my_run.id
        )
        print(f"Run status: {keep_retrieving_run.status}")

        if keep_retrieving_run.status == "completed":
            print("\n")

            # Step 7: Retrieve the Messages added by the Assistant to the Thread
            all_messages = client.beta.threads.messages.list(
                thread_id=my_thread.id
            )

            print("------------------------------------------------------------ \n")

            print(f"User: {my_thread_message.content[0].text.value}")
            print(f"Assistant: {all_messages.data[0].content[0].text.value}")

            break
        elif keep_retrieving_run.status == "queued" or keep_retrieving_run.status == "in_progress":
            pass
        else:
            print(f"Run status: {keep_retrieving_run.status}")
            break

    return {
        "User:" : my_thread_message.content[0].text.value,
        "Assistant:" : all_messages.data[0].content[0].text.value
    }
