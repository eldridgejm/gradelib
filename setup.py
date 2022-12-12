from setuptools import setup, find_packages

setup(
    name="gradelib",
    version="0.3.0",
    packages=find_packages(),
    install_requires=["pandas", "numpy", "bokeh"],
)
