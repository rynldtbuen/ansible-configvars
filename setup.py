from setuptools import setup, find_packages

setup(
    name='cl_vx_config',
    version='v0.1-beta',
    author='Reynold Tabuena',
    author_email='rynldtbuen@gmail.com',
    description=(
        '''
        Simplify configurations variable defined in master.yml
        to use in Cumulus EVPN VXLAN Deployment
        '''
    ),
    url='https://github.com/rynldtbuen/cl_vx_config',
    download_url=(
        'https://github.com/rynldtbuen/cl_vx_config/archive/v0.1.tar.gz'
    ),
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'ansible==2.7.8',
        'napalm',
        'napalm-ansible',
        'napalm-vyos',
        'ruamel.yaml'
    ],
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 4 - Beta'
    ],
)
