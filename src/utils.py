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
    Q:
    The following is the main code that requires unit tests:

    Main Code:
    def multiply(a, b):
        res = 0
        for _ in range(abs(b)):
            res = add(res, a)
        return res if b > 0 else -res

    The main code depends on the following dependency code(s). Inspect these as they may influence the
    behavior of the main code and require their own unit tests:

    def add(a, b):
        return a + b

    Your task:
    1. Generate separate unit test files for the main code and its dependencies. 
    2. Use the naming convention `test_<module_or_function_name>.py`.
    3. Organize the test files in folders based on the original project structure, e.g., `tests/utils/test_math_utils.py`.
    4. Ensure the test cases cover edge cases, typical usage, and error scenarios.
    5. Provide the test cases in Python-compatible format, using `unittest` or `pytest`.

    Strictly follow the example below. Do not add any redundant sentences.
    A:
    File: tests/utils/test_add.py
    ```
    import unittest

    def add(a, b):
        return a + b

    class TestAdd(unittest.TestCase):
        
        def test_add_positive_numbers(self):
            self.assertEqual(add(2, 3), 5)

        def test_add_negative_numbers(self):
            self.assertEqual(add(-1, -1), -2)

        def test_add_positive_and_negative(self):
            self.assertEqual(add(-1, 1), 0)

        def test_add_zero(self):
            self.assertEqual(add(0, 0), 0)
            self.assertEqual(add(5, 0), 5)
            self.assertEqual(add(0, 5), 5)

        def test_add_large_numbers(self):
            self.assertEqual(add(1_000_000, 1_000_000), 2_000_000)

    if __name__ == '__main__':
        unittest.main()
    ```
    
    File: tests/utils/test_multiply.py
    ```
    import unittest

    def add(a, b):
        return a + b

    def multiply(a, b):
        res = 0
        for _ in range(abs(b)):
            res = add(res, a)
        return res if b > 0 else -res

    class TestMultiply(unittest.TestCase):
        
        def test_multiply_positive_numbers(self):
            self.assertEqual(multiply(3, 4), 12)

        def test_multiply_negative_numbers(self):
            self.assertEqual(multiply(-3, -4), 12)

        def test_multiply_positive_and_negative(self):
            self.assertEqual(multiply(-3, 4), -12)
            self.assertEqual(multiply(3, -4), -12)

        def test_multiply_with_zero(self):
            self.assertEqual(multiply(0, 5), 0)
            self.assertEqual(multiply(5, 0), 0)
            self.assertEqual(multiply(0, 0), 0)

        def test_multiply_large_numbers(self):
            self.assertEqual(multiply(1_000, 1_000), 1_000_000)

        def test_multiply_by_one(self):
            self.assertEqual(multiply(1, 999), 999)
            self.assertEqual(multiply(999, 1), 999)

        def test_multiply_by_negative_one(self):
            self.assertEqual(multiply(-1, 999), -999)
            self.assertEqual(multiply(999, -1), -999)

    if __name__ == '__main__':
        unittest.main()
    ```
    
    Q:
    The following is the main code that requires unit tests:

    Main Code:
    {main_code}

    The main code depends on the following dependency code(s). Inspect these as they may influence the
    behavior of the main code and require their own unit tests:
    
    {dependency_code}

    Your task:
    1. Generate separate unit test files for the main code and its dependencies. 
    2. Use the naming convention `test_<module_or_function_name>.py`.
    3. Organize the test files in folders based on the original project structure, e.g., `tests/utils/test_math_utils.py`.
    4. Ensure the test cases cover edge cases, typical usage, and error scenarios.
    5. Provide the test cases in Python-compatible format, using `unittest` or `pytest`.
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
