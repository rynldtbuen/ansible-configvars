from setuptools import setup

setup(
    name='cl_vx_config',
    version='0.1',
    description=(
        '''
        Simplify configurations variable defined in master.yml
        to use in Cumulus EVPN VXLAN Deployment
        '''
    ),
    author='Reynold Tabuena',
    author_email='rynldtbuen@gmail.com',
    license='MIT',
    packages=['cl_vx_config', 'cl_vx_config.utils'],
    install_requires=[
        'ansible==2.7'
        'napalm',
        'napalm-ansible',
        'napalm-vyos',
        'ruamel.yaml'
        ],
    zip_safe=False)
