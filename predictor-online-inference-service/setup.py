"""
Setup configuration for predictor-online-inference-service.
"""

from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]


setup(
    name="predictor-online-inference-service",
    version="1.0.0",
    author="Sentiment Analyzer Team",
    description="Real-time and batch ML inference service for event realization predictions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sentiment-analyzer/predictor-online-inference-service",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "predictor-service=src.main:main",
        ],
    },
)

