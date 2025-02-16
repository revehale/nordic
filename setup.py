from setuptools import setup, find_packages
import os

def read_requirements():
    with open('requirements.txt') as f:
        return f.read().splitlines()

setup(
    name="nordic",
    version="0.1.7",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'nordic=nordic.nor:main',
        ],
    },
    author="Revehale",
    description="A Norwegian-English dictionary command line tool",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/revehale/nordic",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
