"""
Root conftest for backend tests.
Adds support for BDD-style Describe*/it_* test naming alongside Test*/test_* naming.

This conftest is intentionally minimal and adds no fixtures that would conflict
with the existing app/tests/conftest.py.
"""
from __future__ import annotations

import pytest


def pytest_collect_file(parent, file_path):
    """Allow collecting test files with standard names."""
    return None


def pytest_collection_modifyitems(items):
    """
    No-op hook; collection is configured via pytest.ini.
    BDD Describe*/it_* classes and methods are collected because
    pytest_configure adds them to the collection patterns.
    """
    pass


def pytest_configure(config):
    """
    Extend pytest collection to support BDD-style Describe*/it_* naming.

    Adds 'Describe' class prefix and 'it_' function prefix to the existing
    collection patterns without replacing Test*/test_* patterns.
    """
    # Extend class collection to also pick up Describe* classes
    ini = config.inicfg

    # Update python_classes to include Describe*
    existing_classes = config.getini("python_classes")
    if "Describe" not in " ".join(existing_classes):
        config.addinivalue_line("python_classes", "Describe*")

    # Update python_functions to include it_*
    existing_funcs = config.getini("python_functions")
    if "it_" not in " ".join(existing_funcs):
        config.addinivalue_line("python_functions", "it_*")
