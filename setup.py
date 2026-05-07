#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages


# Long description from README
long_description = ""
here = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(here, "README.md")
if os.path.exists(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

# Read version from source file (avoids import during isolated build)
about = {}
version_file = os.path.join(here, "xqr", "_version.py")
if os.path.exists(version_file):
    with open(version_file, encoding="utf-8") as f:
        exec(f.read(), about)
__version__ = about.get("__version__", "0.0.0")

setup(
    name="xqr-z",
    version=__version__,
    description="高性能二维码生成与解码库（numpy 加速，支持中文）",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/QuantumEdgeCode/xqr",
    author="Deepseek-V4-Flash · 江城庄稼汉",
    author_email="",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    keywords="qrcode qr code decode 二维码 生成 解码 中文 artistic animated numpy",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=8.0",
        "numpy>=1.17",
        "opencv-python>=4.5",
    ],
    extras_require={
        "dev": ["pytest"],
        "svg": ["qrcode[pil]"],
    },
    entry_points={
        "console_scripts": [
            "xqr=xqr.cli:main",
        ],
    },
    project_urls={
        "Source": "https://github.com/QuantumEdgeCode/xqr",
        "Bug Reports": "https://github.com/QuantumEdgeCode/xqr/issues",
    },
)
