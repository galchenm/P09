from setuptools import setup, find_packages

setup(
    name='autoprocessing',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'pyyaml',
        'numpy',
        'fabio',
        'gemmi',
    ],
    include_package_data=True,
    package_data={
        'autoprocessing': ['templates/*', '*.yaml'],  # include templates and yaml config files
    },
    entry_points={
        'console_scripts': [
            'autoprocessing=autoprocessing.autoprocessing:main',
            'serial=autoprocessing.serial:main',
            'xds=autoprocessing.xds:main',
            'wedges=autoprocessing.wedges:main',
        ],
    },
    python_requires='>=3.6',
)
