from setuptools import find_packages, setup

setup(
    name='software_manager',
    version='0.1',
    description='Software Manager for Cisco IOS/IOS-XE devices',
    author='Alexander Ignatov',
    license='MIT',
    install_requires=[
        'scrapli[paramiko]',
        'rq-scheduler',
        'xlsxwriter',
    ],
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/alsigna/netbox-software-manager',
)
