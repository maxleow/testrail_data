import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="testrail-data",
    version="0.0.7",
    install_requires=[
        "pandas",
        "testrail-api>=1.10",
    ],
    author="Max Leow",
    author_email="maxengiu@outlook.com",
    description="Pandas DataFrame integrated API wrapper for Testrail",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/maxleow/testrail_data",
    project_urls={
        "Bug Tracker": "https://github.com/maxleow/testrail_data/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    python_requires=">=3.7",
)
