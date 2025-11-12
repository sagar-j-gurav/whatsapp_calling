# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import re


class WhatsAppNumber(Document):
	def validate(self):
		"""Validate phone number format and extract country code"""
		self.validate_phone_number()
		self.extract_country_code()

	def validate_phone_number(self):
		"""Ensure phone number is in E.164 format"""
		if not self.phone_number:
			return

		# Remove any spaces, hyphens, or parentheses
		cleaned = re.sub(r'[\s\-\(\)]', '', self.phone_number)

		# Check if it starts with +
		if not cleaned.startswith('+'):
			frappe.throw('Phone number must be in E.164 format (e.g., +919876543210)')

		# Check if rest are digits
		if not cleaned[1:].isdigit():
			frappe.throw('Phone number must contain only digits after +')

		# Update with cleaned version
		self.phone_number = cleaned

	def extract_country_code(self):
		"""Extract country code from phone number"""
		if not self.phone_number:
			return

		# Simple extraction (first 1-3 digits after +)
		# This is a simplified version - you may want to use a library like phonenumbers
		match = re.match(r'\+(\d{1,3})', self.phone_number)
		if match:
			self.country_code = f"+{match.group(1)}"

	def on_update(self):
		"""Update last_used when number is modified"""
		pass

	def get_access_token(self):
		"""Get access token for this number or fall back to default"""
		if self.access_token:
			return self.get_password('access_token')
		else:
			settings = frappe.get_single("WhatsApp Settings")
			return settings.get_password('default_access_token')
