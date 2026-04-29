"""
Test configuration for ContentProcessorWorkflow tests.
"""
import sys
from pathlib import Path

# Add ContentProcessorWorkflow src to path
workflow_src_path = Path(__file__).resolve().parent.parent.parent / "ContentProcessorWorkflow" / "src"
if str(workflow_src_path) not in sys.path:
    sys.path.insert(0, str(workflow_src_path))

pytest_plugins = ["pytest_mock"]
