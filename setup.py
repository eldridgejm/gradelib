from setuptools import setup, find_packages

setup(
    name="gradelib",
    version="0.2.1",
    packages=find_packages(),
    install_requires=["pandas", "numpy", "matplotlib"],
)
