from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='cumulus_vxconfig',
    version='v1.0.6',
    author='Reynold Tabuena',
    author_email='rynldtbuen@gmail.com',
    description=(
        '''
        Transform and simplify configuration variables.
        '''
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/rynldtbuen/cumulus-vxconfig',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'ansible==2.9.20',
        'napalm',
        'napalm-ansible',
        'napalm-vyos',
        'ruamel.yaml'
    ],
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        "console_scripts": [
            "cumulus_getconfig=cumulus_vxconfig.cli:main"
        ]
    }
)
