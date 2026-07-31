import os
import sys

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dashboard.streamlit_app import main

if __name__ == "__main__":
    main()
else:
    main()
