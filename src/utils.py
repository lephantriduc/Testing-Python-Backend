import hashlib
import json
import os
import time
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from src.testsuite import *

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)

def generate_test_with_ai(main_code: str, dependency_code: list[str]):
    formatted_dependencies = "\n\n".join(
        f"Dependency Code {i+1}:\n{dep}" for i, dep in enumerate(dependency_code)
    )

    prompt = (
        "A test suite contains a set of test cases, each test case is \n"
        "represented by a set of arguments to be passed to some function, "
        "method or constructor (test object). Find a test suite that yields "
        "the highest branch coverage (i.e. it should consider all execution "
        "path or cases, including possible exceptions) for the following "
        f"test object:\n```python\n{main_code}\n```\n"
    )

    if dependency_code != []:
        prompt += (
            "As for context, here is other relevant codes that the object might depend on:\n"
            f"```python\n{' '.join(dependency_code)}\n```\n"
        )

    chat_completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=TestSuite
    )

    return chat_completion.choices[0].message.parsed


def pyvalue_interpret(x: PyValue):
    val_type, val = x.value_type, x.encoded_value
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


def reformat_gpt_response(suite: TestSuite, module_path: str) -> dict:
    id = hashlib.md5(f"{module_path}{time.time()}".encode()).hexdigest()
    
    res = {
        'suite_id': id,
        'module_path': module_path,
        'object_name': suite.object_name,
        'object_type': suite.object_type,
        'test_cases': [],
    }

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
    
    res['coverage'] = 'N/A'

    return res


def run_coverage_and_get_results(tests_dir="../uploads/examples"):
    coverage_file = os.path.join(tests_dir, ".coverage")

    if os.path.exists(coverage_file):
        os.remove(coverage_file)

    # TODO: y bug
    subprocess.run(["python", "-m", "coverage", "run", "-m", "unittest", "discover", 'src/tests'], cwd=tests_dir, check=True)
    subprocess.run(["coverage", "json", "-o", os.path.join(tests_dir, "coverage.json")], check=True)

    with open(os.path.join(tests_dir, "coverage.json"), "r") as f:
        coverage_data = json.load(f)

    # # Extract relevant coverage metrics
    # covered_statements = coverage_data["totals"]["covered"]
    # coverage_percentage = coverage_data["totals"]["percent"]
    #
    # return {
    #     "covered_statements": covered_statements,
    #     "coverage_percentage": coverage_percentage
    # }

if __name__ == "__main__":
    print(run_coverage_and_get_results())
