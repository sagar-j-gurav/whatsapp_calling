# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class WhatsAppCall(Document):
	def validate(self):
		"""Calculate duration and cost"""
		if self.answered_at and self.ended_at:
			self.duration_seconds = self.calculate_duration()

		if self.direction == "Outbound" and self.duration_seconds:
			self.cost = self.calculate_cost()

	def calculate_duration(self):
		"""Calculate call duration in seconds"""
		start = frappe.utils.get_datetime(self.answered_at)
		end = frappe.utils.get_datetime(self.ended_at)
		return int((end - start).total_seconds())

	def calculate_cost(self):
		"""Calculate cost based on duration (inbound calls are free)"""
		if self.direction == "Inbound":
			return 0.0

		# TODO: Implement rate calculation based on country
		# For now, using India rates: ₹0.50 per minute
		minutes = self.duration_seconds / 60
		rate_per_minute = 0.50
		return round(minutes * rate_per_minute, 2)

	def after_insert(self):
		"""Link call to Lead timeline"""
		if self.lead:
			self.add_comment(
				"Info",
				f"WhatsApp Call {self.status}: {self.duration_seconds or 0}s"
			)

	def on_update(self):
		"""Update related records on status change"""
		if self.has_value_changed('status'):
			# Update call permission usage
			if self.status == 'Answered':
				self.update_call_permission_usage()

			# Update WhatsApp Number last_used
			if self.business_number:
				self.update_business_number_usage()

	def update_call_permission_usage(self):
		"""Increment call counter in permission record"""
		try:
			permission = frappe.get_doc("Call Permission", {
				"customer_number": self.customer_number,
				"business_number": self.business_number
			})

			permission.calls_in_24h = (permission.calls_in_24h or 0) + 1
			permission.last_call_at = frappe.utils.now()
			permission.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to update call permission: {str(e)}")

	def update_business_number_usage(self):
		"""Update last_used timestamp and monthly usage"""
		try:
			wa_number = frappe.get_doc("WhatsApp Number", self.business_number)
			wa_number.last_used = frappe.utils.now()

			# Update monthly usage (cost)
			if self.cost:
				current_usage = wa_number.current_month_usage or 0
				wa_number.current_month_usage = current_usage + self.cost

			wa_number.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to update business number: {str(e)}")
