from setuptools import setup
from setuptools import find_packages

required = [
    "freezegun",
    "numpy",
    "pandas",
    "pydocstyle",
    "pytest",
    "pytest-cov",
    "pylint==2.8.3",
    "delphi-utils",
    "covidcast",
    "delphi-epidata"
]

setup(
    name="delphi_hhs",
    version="0.1.0",
    description="SHORT DESCRIPTION",
    author="",
    author_email="",
    url="https://github.com/cmu-delphi/covidcast-indicators",
    install_requires=required,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
    ],
    packages=find_packages(),
)
