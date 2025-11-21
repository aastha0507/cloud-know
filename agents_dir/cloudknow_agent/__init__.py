"""CloudKnow ADK Agent Package."""
import sys
import os

# Add project root to Python path before any imports
# This ensures that imports like "from cloudknow_tools.tools" work correctly
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_project_root = os.path.dirname(_current_dir)

# Ensure project root is in Python path (at the beginning for priority)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

__all__ = []

