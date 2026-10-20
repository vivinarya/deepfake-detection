import runpy
import os

if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    target = os.path.join(current_dir, "streamlit_app.py")
    runpy.run_path(target, run_name="__main__")