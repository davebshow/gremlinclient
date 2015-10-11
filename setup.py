from setuptools import setup


setup(
    name="gremlinclient",
    version="0.0.1",
    url="",
    license="MIT",
    author="davebshow",
    author_email="davebshow@gmail.com",
    description="Python driver for TP3 Gremlin Server",
    long_description=open("README.txt").read(),
    packages=["gremlinclient", "tests"],
    install_requires=[
        "tornado==4.2.1"
    ],
    test_suite="tests",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ]
)
