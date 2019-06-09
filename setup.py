from setuptools import setup, find_packages

setup(
    name='cl_vx_config',
    version='v1.0',
    author='Reynold Tabuena',
    author_email='rynldtbuen@gmail.com',
    description=(
        '''
        A python script that simplify the configuration variables defined in
        master.yml and use it as a custom filter in
        https://github.com/rynldtbuen/cumulus-evpn-vxlan-ansible
        to load the simplified configuration variables to deploy
        Cumulus EVPN VXLAN in Symmetric Routing
        '''
    ),
    url='https://github.com/rynldtbuen/cl-vx-config',
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
