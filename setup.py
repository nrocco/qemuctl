#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name="qemuctl",
    description="a command line tool to manage qemu images",
    version="0.0.1",
    author="Nico Di Rocco",
    author_email="dirocco.nico@gmail.com",
    url="https://github.com/nrocco",
    license="Private",
    long_description="a command line tool to manage qemu images",
    include_package_data=True,
    install_requires=[
        "click",
        "flask",
        "requests",
    ],
    extras_require={
        "develop": [
            "pytest",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "qemuctl = qemu.cli:cli",
        ]
    },
    packages=find_packages(exclude=["tests"]),
    test_suite="tests",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
)
