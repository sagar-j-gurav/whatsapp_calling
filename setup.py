from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in whatsapp_calling/__init__.py
from whatsapp_calling import __version__ as version

setup(
	name="whatsapp_calling",
	version=version,
	description="WhatsApp voice calling integration for ERPNext CRM",
	author="Your Company",
	author_email="support@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
