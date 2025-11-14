# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppSettings(Document):
	def on_load(self):
		"""Set webhook URL dynamically"""
		site_url = frappe.utils.get_url()
		self.webhook_url = f"{site_url}/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook"

	def validate(self):
		"""Validate Janus connection"""
		if self.janus_http_url:
			self.test_janus_connection()

	@frappe.whitelist()
	def test_janus_connection(self):
		"""Test if Janus is accessible"""
		import requests
		try:
			response = requests.get(f"{self.janus_http_url}/info", timeout=5)
			if response.status_code != 200:
				frappe.msgprint("Warning: Cannot connect to Janus Gateway", indicator='orange')
		except Exception as e:
			frappe.msgprint(f"Warning: Janus connection failed: {str(e)}", indicator='orange')

	@frappe.whitelist()
	def get_webhook_test_url(self):
		"""Get webhook URL and verify token for testing"""
		site_url = frappe.utils.get_url()
		webhook_url = f"{site_url}/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook"
		verify_token = self.get_password('webhook_verify_token')

		return {
			"webhook_url": webhook_url,
			"verify_token": verify_token
		}
