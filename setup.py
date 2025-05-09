# setup.py
from setuptools import setup, find_packages

setup(
    name="whatsapp_ai_agent",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # (optional) add any dependencies here that you want always installed
        # e.g. "fastapi", "uvicorn", "langchain", etc.
    ],
    entry_points={
        "console_scripts": [
            # if you want a `launch-all = launch_all:main` CLI, etc.
        ]
    },
)
