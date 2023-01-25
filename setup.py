from setuptools import find_packages, setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="netbox-plugin-software-manager",
    version="0.0.4",
    description="Software Manager for Cisco IOS/IOS-XE devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alexander Ignatov",
    license="MIT",
    install_requires=[
        "scrapli[paramiko]",
        "scrapli[textfsm]",
    ],
    packages=find_packages(),
    include_package_data=True,
    url="https://github.com/alsigna/netbox-software-manager",
)
