"""Shared pytest fixtures."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast isolated unit tests")
    config.addinivalue_line("markers", "integration: tests requiring external services")
