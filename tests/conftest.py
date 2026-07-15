import os
import sys

# App modules import as ``utils.x`` / ``models.x`` with src/ on the path,
# matching how streamlit run src/web_app.py and src/main.py execute.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
