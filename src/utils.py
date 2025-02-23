import hashlib
import json
import os
import time
import subprocess

from multipart import file_path
from openai import OpenAI
from dotenv import load_dotenv
from sphinx.util.rst import textwidth
from twisted.logger import capturedLogs

from src.parse import suite_to_script
from src.testsuite import *

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)


def generate_test_with_ai(main_code: str, dependency_code: list[str]):
    formatted_dependencies = "\n\n".join(
        f"Dependency Code {i + 1}:\n{dep}" for i, dep in enumerate(dependency_code)
    )

    prompt = (
        "A test suite contains a set of test cases, each test case is \n"
        "represented by a set of arguments to be passed to some function, "
        "method or constructor (test object). Find a test suite that yields "
        "the highest branch coverage that uses the least amount of test cases "
        "(i.e. it should consider all execution "
        "path or cases, including possible exceptions) for the following "
        f"test object:\n```python\n{main_code}\n```\n"
    )

    if dependency_code != []:
        tmp = '\n\n'.join(dependency_code)
        prompt += (
            "As for context, here is other relevant codes that the object might depend on:\n"
            f"```python\n{tmp}\n```\n"
        )

    chat_completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=TestSuite
    )

    return chat_completion.choices[0].message.parsed

def regenerate_test_with_ai(main_code: str, dependency_code: list[str], missed_lines: str):
    prompt = (
        "A test suite contains a set of test cases, each test case is \n"
        "represented by a set of arguments to be passed to some function, "
        "method or constructor (test object)."
        
        f"test object:\n```python\n{main_code}\n```\n"
        
        f"A test suite made for this code has missed the following lines: {missed_lines}" 
        "Generate a new test suite to specifically deal with those missed lines."
        ""

    )
    #
    # if dependency_code != []:
    #     tmp = '\n\n'.join(dependency_code)
    #     prompt += (
    #         "As for context, here is other relevant codes that the object might depend on:\n"
    #         f"```python\n{tmp}\n```\n"
    #     )


    chat_completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=TestSuite
    )

    return chat_completion.choices[0].message.parsed

def pyvalue_interpret(x: PyValue):
    # print(f"Pyvalue is: {x}")
    val_type, val = x.value_type, x.encoded_value
    # print(f"val_type: {val_type}")
    # print(f"val: {val}")
    try:
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        if val_type == PyValueType.INT:
            return int(val)
        if val_type == PyValueType.FLOAT:
            return float(val)
        if val_type == PyValueType.STR:
            return val
        if val_type == PyValueType.BOOL:
            return val.lower() not in ["false", ""]
        if val_type == PyValueType.NONE:
            return None
        if val_type == PyValueType.LIST:
            # TODO: can you do it better?
            return json.loads(val)
        if val_type == PyValueType.DICT:
            return json.loads(val)
    except:
        print("Something went wrong with pyvalue interpretation")


def reformat_gpt_response(suite: TestSuite, module_path: str, is_overwriting: bool) -> dict:
    id = hashlib.md5(f"{module_path}{time.time()}".encode()).hexdigest()

    res = {
        'suite_id': id,
        'module_path': module_path,
        'object_name': suite.object_name,
        'object_type': suite.object_type,
        'test_cases': [],
    }

    path_parts = module_path.split("/", maxsplit=1)
    repo_name = path_parts[0]
    path_to_file = path_parts[1]

    for case in suite.test_cases:
        e = {'test_args': {}}
        for arg in case.test_args:
            e['test_args'][arg.arg_name] = \
                pyvalue_interpret(arg.arg_value)
        behavior = case.return_value_or_exception
        if isinstance(behavior, PyException):
            e['exception'] = behavior.ex_type
            e['return_value'] = None
        else:
            e['exception'] = None
            e['return_value'] = \
                pyvalue_interpret(behavior)
        res['test_cases'].append(e)

    suite_to_script(res, is_overwriting)

    # print(repo_name, path_to_file)
    # print(subprocess.run(["pwd"], capture_output=True, text=True))
    cov_score, missed_lines = run_coverage_and_get_results(repo_name, path_to_file)
    res['coverage'] = cov_score
    res['missed_lines'] = missed_lines.rstrip()

    return res

# def add_coverage_and_missed_lines(suite: dict):
#     suite_to_script(suite)
#     cov_score, missed_lines = run_coverage_and_get_results(ddk)


def run_coverage_and_get_results(repo_name, file_path):
    tests_dir = f"uploads/{repo_name}"
    print(f"Where the file is: {file_path}")
    coverage_file = os.path.join(tests_dir, ".coverage")

    if os.path.exists(coverage_file):
        os.remove(coverage_file)

    subprocess.run(["coverage", "run", "-m", "pytest", "tests/"], cwd=tests_dir)
    coverage_report = subprocess.run(["coverage", "report", "-m"], cwd=tests_dir, capture_output=True, text=True)

    with open(f"{tests_dir}/tests/coverage.log", "w") as f:
        f.write(str(coverage_report.stdout))

    cov_result = subprocess.run(["awk", f'$1 == "{file_path}" {{if (NF > 4) print $4, substr($0, index($0, $5)); else print $4, "NONE"}}', "coverage.log"], cwd=f"{tests_dir}/tests",
                            capture_output=True, text=True).stdout
    cov_score, missed_lines = cov_result.split(maxsplit=1)

    return cov_score, missed_lines


if __name__ == "__main__":
    file_path = "src/__init__.py"
    repo_name = "examples"
    tests_dir = f"../uploads/{repo_name}"
    result = subprocess.run(["awk", f'$1 == "{file_path}" {{if (NF > 4) print $4, substr($0, index($0, $5)); else print $4, "NONE"}}', "coverage.log"], cwd=f"{tests_dir}/tests",
                   capture_output=True, text=True).stdout
    cov_score, missed_lines = result.split(maxsplit=1)
    print(cov_score, missed_lines, sep='\n')
