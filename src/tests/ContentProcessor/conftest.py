"""
Test configuration for ContentProcessor tests.
"""
import sys
import os

# Add ContentProcessor src to path
contentprocessor_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'ContentProcessor', 'src')
)
sys.path.insert(0, contentprocessor_path)

# Copy pytest plugins from original conftest
pytest_plugins = ["pytest_mock"]
