import sys
import subprocess
import textwrap
import pytest
from ....components.tdd_kit import MindoffTestCase
import uuid
import shutil
import subprocess
import sys
from pathlib import Path
import filecmp
import tempfile
import importlib
import os

# @pytest.fixture(scope="class")
# def mindoff_project(tmp_path_factory):
#     """Create a Django-Mindoff project once per test class and clean it up at the end."""
#     # System temp folder
#     tmp_dir = tmp_path_factory.getbasetemp()
#     project_name = f"test_proj_{uuid.uuid4().hex}"
#     project_dir = tmp_dir / project_name
#     project_dir.mkdir()

#     # Init project
#     subprocess.run(
#         ["django-mindoff", "init", "--minimal"],
#         cwd=project_dir,
#         check=True,
#     )

#     yield project_dir

#     # Cleanup
#     shutil.rmtree(tmp_dir, ignore_errors=True)


class TestApiOutlineCreator(MindoffTestCase):
    """End-to-end tests for create_api_outline command."""

    def test_create_api_outline_with_progress(self):
        apps = ["single_level_app"]
        api_names = ["MindOffSampleAPI"]
        project_dir = Path("D:/02_Work/08_Django_Mindoff_Kit__vTest")
        self._create_app(project_dir, apps=apps)

        # === Step 1: Copy reference outlines to app ===
        test_data_root = Path(__file__).parent / "_test_create_api_outline"
        for app_name in apps:
            test_app_dir = test_data_root / app_name
            temp_app_dir = project_dir / "apps" / app_name
            if test_app_dir.exists():
                self._copy_test_data_to_temp_app(test_app_dir, temp_app_dir)

        # === Step 2: Run CLI command ===
        mindoff_py = project_dir / "mindoff.py"
        subprocess.run(
            ["python", mindoff_py, "createapioutline"],
            cwd=project_dir,
            check=True,
        )

        # === Step 3: Recursively validate __api_outlines__.py ===
        for idx, app_name in enumerate(apps):
            api_name = api_names[idx]
            temp_app_dir = project_dir / "apps" / app_name
            actual_file = temp_app_dir / "components" / "__api_outlines__.py"
            expected_file = temp_app_dir / "components" / "expected_output.py"
            assert actual_file.exists(), f"Missing actual_file at {actual_file}"
            assert expected_file.exists(), f"Missing expected_file at {expected_file}"
            actual = self._load_api_outlines(actual_file)
            expected = self._load_api_outlines(expected_file)

            assert isinstance(actual, dict), f"{actual_file} has no dict API_OUTLINES"
            assert isinstance(
                expected, dict
            ), f"{expected_file} has no dict API_OUTLINES"

            assert api_name in actual, f"{api_name} not found in {actual_file}"
            assert api_name in expected, f"{api_name} not found in {expected_file}"

            actual_len = len(actual[api_name])
            expected_len = len(expected[api_name])

            assert actual_len == expected_len, (
                f"Mismatch in API_OUTLINES[{api_name}] length:\n"
                f"Got: {actual_len}\nExpected: {expected_len}"
            )

    def _create_app(self, project_dir, apps):
        subprocess.run(
            ["python", "mindoff.py", "createapp", *apps],
            cwd=project_dir,
            check=True,
        )

    def _copy_test_data_to_temp_app(self, test_app_dir, temp_app_dir):
        for test_app_item in test_app_dir.iterdir():
            temp_app_item = temp_app_dir / test_app_item.name
            if temp_app_item.exists():
                if temp_app_item.is_file():
                    temp_app_item.unlink()
                else:
                    shutil.rmtree(temp_app_item)
            if test_app_item.is_dir():
                shutil.copytree(test_app_item, temp_app_item)
            else:
                shutil.copy2(test_app_item, temp_app_item)

    def _load_api_outlines(self, file_path: Path):
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # execute the module
        return getattr(module, "API_OUTLINES", None)


# WEIGHT VALIDATION

# -- FUNCTION READING CHECKS
# function_from_same_class
# function_from_same_class_extends_to_function_from_same_file
# function_from_same_class_extends_to_function_from_another_file
# function_from_same_file
# function_from_same_file_extends_to_function_from_same_file
# function_from_same_file_extends_to_function_from_another_file
# function_from_different_file
# function_from_different_file_extends_to_function_from_same_file
# function_from_different_file_extends_to_function_from_another_file


# 1. single level update_progress no loop -- valid
"""
    # code
    update_progress("init", weight=3)
    update_progress("process", weight=6)
    update_progress("finish")
    return mo_response_kit.json_response(
        code="SUCCESS", category="success", data={}
    )
"""

# 2. single level update_progress inside loop -- valid
"""
    # code
    update_progress("init", weight=3)
    for i in range(10):
        update_progress("process", weight=6)
    update_progress("finish", weight=1)
    return mo_response_kit.json_response(
        code="SUCCESS", category="success", data={}
    )
"""


# 3. multi level update_progress inside loop-- valid
"""
    # code
    update_progress("init", weight=25)
    for i in range(10):
        self._sub_function()
        update_progress("process", weight=50)
    from .external_function import external_function
    x = 5
    external_function(x)
    update_progress("finish", weight=25)
    return mo_response_kit.json_response(
        code="SUCCESS", category="success", data={}
    )
    
def _sub_function(self):
    update_progress("init", weight=25)
    for i in range(10):
        update_progress("process", weight=50)
    update_progress("finish", weight=25)
    return mo_response_kit.json_response(
        code="SUCCESS", category="success", data={}
    )

"""
# The External Functions
# single level -- no loop
"""
-- # code
def external_function(x):
    update_progress("init", weight=25)
    y = x * 2
    return y
"""

# single level -- with loop


# multi level
"""
-- # code
def external_function(x):
    update_progress("init", weight=25)
    y = x * 2
    return y
"""
