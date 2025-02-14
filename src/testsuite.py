from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TestObjectType(str, Enum):
    METHOD = "method"
    FUNCTION = "function"
    CONSTRUCTOR = "constructor"


class PyValueType(str, Enum):
    INT = "int"
    FLOAT = "float"
    # COMPLEX = "complex"
    STR = "str"
    BOOL = "bool"
    NONE = "NoneType"
    LIST = "list"
    # TUPLE = "tuple"
    # SET = "set"
    DICT = "dict"
    # CLASS = "class"


class PyValue(BaseModel):
    value_type: PyValueType
    encoded_value: str


class TestCaseArg(BaseModel):
    arg_name: str
    arg_value: PyValue


class PyException(BaseModel):
    ex_type: str
    ex_message: Optional[str]


class ReturnValue(PyValue, BaseModel):
    pass


class TestCase(BaseModel):
    explanation: Optional[str]
    test_args: list[TestCaseArg]
    return_value_or_exception: ReturnValue | PyException


class TestSuite(BaseModel):
    object_name: str
    object_type: TestObjectType
    test_cases: list[TestCase]
