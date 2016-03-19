from setuptools import setup


setup(
    name="gremlinclient",
    version="0.2.5",
    url="",
    license="MIT",
    author="davebshow",
    author_email="davebshow@gmail.com",
    description="Python driver for TP3 Gremlin Server",
    long_description=open("README.txt").read(),
    packages=["gremlinclient", "gremlinclient.aiohttp_client",
              "gremlinclient.tornado_client", "tests"],
    install_requires=[
        "tornado==4.3"
    ],
    test_suite="tests",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ]
)
