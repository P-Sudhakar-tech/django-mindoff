from setuptools import setup, find_packages
import pathlib

BASE_DIR = pathlib.Path(__file__).parent.resolve()
long_description = (BASE_DIR / "README.md").read_text(encoding="utf-8")

setup(
    name="django-mindoff",
    version="0.1.0",
    packages=find_packages(include=["django_mindoff", "django_mindoff.*"]),
    description="A developer-focused Django automation kit with CLI tools.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your@email.com",
    url="https://github.com/yourusername/django-mindoff",  # Optional
    license="MIT",
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.9",
    install_requires=[
        "Django>=4.0",
    ],
    entry_points={
        "console_scripts": [
            "django-mindoff = django_mindoff.views:main",  # CLI command: mindoff createapp ...
        ]
    },
    include_package_data=True,
)
