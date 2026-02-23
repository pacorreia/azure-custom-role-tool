import runpy
import sys

import pytest

from azure_custom_role_tool import cli


def test_main_entrypoint(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["custom-role-designer"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("azure_custom_role_tool", run_name="__main__")

    assert exc.value.code == 0
