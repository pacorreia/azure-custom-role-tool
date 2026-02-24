"""Setup configuration for Azure Custom Role Designer package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="azure-custom-role-tool",
    version="1.0.0",
    author="OI Technologies Platform Engineering",
    author_email="platform-engineering@example.com",
    description="A powerful CLI tool for creating and managing Azure custom roles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pacorreia/azure-custom-role-tool",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Topic :: System :: Systems Administration",
        "Development Status :: 4 - Beta",
    ],
    python_requires=">=3.8",
    install_requires=[
        "azure-identity>=1.14.0",
        "azure-mgmt-authorization>=4.0.0",
        "azure-mgmt-subscription>=3.1.0",
        "azure-common>=1.1.28",
        "click>=8.1.7",
        "tabulate>=0.9.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.4.2",
        "rich>=13.7.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "azure-custom-role-tool=azure_custom_role_tool.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
