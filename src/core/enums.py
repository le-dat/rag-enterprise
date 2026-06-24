from enum import Enum


class Role(str, Enum):
    MANAGER = "manager"
    STAFF = "staff"


class Department(str, Enum):
    HR = "HR"
    SALES = "Sales"
