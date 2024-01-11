from setuptools import setup, find_packages

setup(
    name="tasktrackerwebui",
    version="0.0.1",
    packages=find_packages(include=["tasktrackerwebui"]),
    package_data={"templates": ["templates/input_task.html"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=["Flask", "requests", "waitress", "gevent"],
    entry_points={"console_scripts": ["tasktrackerwebui=tasktrackerwebui.webui:start"]},
)
