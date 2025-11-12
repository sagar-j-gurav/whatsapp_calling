# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"module_name": "WhatsApp Calling",
			"category": "Modules",
			"label": _("WhatsApp Calling"),
			"color": "#25D366",
			"icon": "octicon octicon-device-mobile",
			"type": "module",
			"description": "Make and receive WhatsApp voice calls from CRM"
		}
	]
