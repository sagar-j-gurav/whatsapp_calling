# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"label": _("Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "WhatsApp Settings",
					"label": _("WhatsApp Settings"),
					"description": _("Configure WhatsApp API and Janus settings")
				},
				{
					"type": "doctype",
					"name": "WhatsApp Number",
					"label": _("WhatsApp Number"),
					"description": _("Manage WhatsApp Business phone numbers")
				}
			]
		},
		{
			"label": _("Calling"),
			"items": [
				{
					"type": "doctype",
					"name": "WhatsApp Call",
					"label": _("WhatsApp Call"),
					"description": _("View call history and recordings")
				},
				{
					"type": "doctype",
					"name": "Call Permission",
					"label": _("Call Permission"),
					"description": _("Manage call permissions")
				}
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "Call Analytics",
					"label": _("Call Analytics"),
					"doctype": "WhatsApp Call",
					"is_query_report": True
				}
			]
		}
	]
