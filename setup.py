from setuptools import setup, find_packages

setup(
    name='pysh',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pysh=pysh:main',
        ],
    },
    author='Rituraj Basak',
    description='A basic Unix shell and Python REPL',
    url="https://codeberg.org/zz/PySh", 
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        "pyreadline3; platform_system=='Windows'",
    ],
)
