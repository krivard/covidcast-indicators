# this file is used only as a hookup for Jenkins. 
# if you are looking for the setup.py file associated with the 
# delphi_facebook python package, see `delphiFacebook/python/setup.py`

from setuptools import setup
from setuptools import find_packages

required = [ "" ]

setup(
    name="facebook",
    version="0.0.1",
    description="Facebook Survey",
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
