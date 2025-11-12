# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta


class CallPermission(Document):
	def validate(self):
		"""Check and update expiration status"""
		self.check_expiration()

	def check_expiration(self):
		"""Check if permission has expired"""
		if self.permission_status == "Granted" and self.expires_at:
			expires = frappe.utils.get_datetime(self.expires_at)
			if expires < datetime.now():
				self.permission_status = "Expired"

	def can_make_call(self):
		"""
		Check if a call can be made with this permission

		Returns:
			tuple: (bool, str) - (can_call, reason)
		"""
		# Check status
		if self.permission_status != "Granted":
			return False, f"Permission status: {self.permission_status}"

		# Check expiration
		if self.expires_at:
			expires = frappe.utils.get_datetime(self.expires_at)
			if expires < datetime.now():
				return False, "Permission expired"

		# Check 24h call limit
		if self.last_call_at:
			last_call = frappe.utils.get_datetime(self.last_call_at)
			hours_since = (datetime.now() - last_call).total_seconds() / 3600

			# Reset counter if 24h passed
			if hours_since >= 24:
				self.calls_in_24h = 0
				self.save(ignore_permissions=True)
			elif self.calls_in_24h >= 5:
				return False, "Daily call limit (5) reached"

		return True, "OK"

	def reset_daily_counters(self):
		"""Reset 24h counters (called by scheduled task)"""
		if self.last_call_at:
			last_call = frappe.utils.get_datetime(self.last_call_at)
			hours_since = (datetime.now() - last_call).total_seconds() / 3600

			if hours_since >= 24:
				self.calls_in_24h = 0
				self.save(ignore_permissions=True)
