try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="compressinja",
    version="0.0.3",
    author="Stanislav Feldman",
    description=("Jinja2 extension that removes whitespace between HTML tags."),
    url="https://github.com/stanislavfeldman/compressinja",
    keywords="jinja2 html compress",
    packages=['compressinja'],
    install_requires=["jinja2"],
)
