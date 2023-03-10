from major.requirements import REQUIREMENTS_MAP
import json
from os import DirEntry, scandir
import pytest


DEGREE_DATA_FILES = list(scandir("./degree_data"))


# ensure degree data's are valid
@pytest.mark.parametrize(
    "file", DEGREE_DATA_FILES, ids=lambda file: "file={}".format(file)
)
def test_degrees(file: DirEntry[str]) -> None:
    data = json.loads(open(file, "r").read())

    requirements = data["requirements"]["major"]

    for requirement in requirements:
        REQUIREMENTS_MAP[requirement["matcher"]].from_json(requirement)


"""Add tests for:

Business administration & all the variants
Business analytics
Finanace
Global business and all the variants
Healthcare Management and all the variants
Information Technology and Systems
Marketing
Supply Chain Management
All the double majors

"""
