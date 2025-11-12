# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from whatsapp_calling.whatsapp_calling.utils.whatsapp_api import WhatsAppAPI


def check_call_permission(customer_number, business_number):
	"""
	Check if business can call customer

	Returns:
		{
			"can_call": True/False,
			"reason": "explanation"
		}
	"""
	# Find permission record
	permission = frappe.db.get_value(
		"Call Permission",
		{
			"customer_number": customer_number,
			"business_number": business_number
		},
		["name", "permission_status", "expires_at", "calls_in_24h", "last_call_at"],
		as_dict=True
	)

	if not permission:
		return {
			"can_call": False,
			"reason": "No call permission. Please request permission first."
		}

	# Check if permission is granted
	if permission.permission_status != "Granted":
		return {
			"can_call": False,
			"reason": f"Permission status: {permission.permission_status}"
		}

	# Check if expired
	if permission.expires_at:
		expires = frappe.utils.get_datetime(permission.expires_at)
		if expires < datetime.now():
			return {
				"can_call": False,
				"reason": "Permission expired. Please request permission again."
			}

	# Check 24h call limit (max 5 calls)
	if permission.last_call_at:
		last_call = frappe.utils.get_datetime(permission.last_call_at)
		if (datetime.now() - last_call).total_seconds() < 86400:  # Within 24 hours
			if permission.calls_in_24h >= 5:
				return {
					"can_call": False,
					"reason": "Daily call limit (5) reached. Please try tomorrow."
				}

	return {"can_call": True, "reason": "OK"}


@frappe.whitelist()
def request_call_permission(lead_name, mobile_number):
	"""
	Send call permission request via WhatsApp template

	Args:
		lead_name: CRM Lead name
		mobile_number: Customer mobile number
	"""
	try:
		lead = frappe.get_doc("Lead", lead_name)
		wa_number = get_company_whatsapp_number(lead.company)

		if not wa_number:
			frappe.throw(_("No WhatsApp number configured"))

		# Check existing permission
		existing = frappe.db.get_value(
			"Call Permission",
			{
				"customer_number": mobile_number,
				"business_number": wa_number.name
			},
			["name", "requests_in_24h", "requests_in_7d", "request_sent_at"],
			as_dict=True
		)

		# Check request limits
		if existing:
			last_request = frappe.utils.get_datetime(existing.request_sent_at)
			hours_since = (datetime.now() - last_request).total_seconds() / 3600

			if hours_since < 24 and existing.requests_in_24h >= 1:
				frappe.throw(_("Can only send 1 request per 24 hours"))

			if hours_since < 168 and existing.requests_in_7d >= 2:  # 7 days
				frappe.throw(_("Can only send 2 requests per 7 days"))

			permission_doc = frappe.get_doc("Call Permission", existing.name)

			# Reset counters if needed
			if hours_since >= 24:
				permission_doc.requests_in_24h = 0
			if hours_since >= 168:
				permission_doc.requests_in_7d = 0
		else:
			# Create new permission record
			permission_doc = frappe.get_doc({
				"doctype": "Call Permission",
				"customer_number": mobile_number,
				"business_number": wa_number.name,
				"company": lead.company,
				"lead": lead_name,
				"permission_status": "Requested",
				"requests_in_24h": 0,
				"requests_in_7d": 0
			})

		# Send WhatsApp template
		wa_api = WhatsAppAPI(
			wa_number.phone_number_id,
			wa_number.get_access_token()
		)

		# Template must be pre-approved in Meta Business Manager
		wa_api.send_template(
			to_number=mobile_number,
			template_name="call_permission_request",
			components=[{
				"type": "button",
				"sub_type": "voice_call",
				"index": 0,
				"parameters": [{
					"type": "action",
					"action": {
						"flow_action_type": "voice_call_request"
					}
				}]
			}]
		)

		# Update permission record
		permission_doc.requests_in_24h += 1
		permission_doc.requests_in_7d += 1
		permission_doc.request_sent_at = frappe.utils.now()

		if existing:
			permission_doc.save()
		else:
			permission_doc.insert()

		frappe.db.commit()

		frappe.msgprint(_("Permission request sent successfully"))
		return {"success": True}

	except Exception as e:
		frappe.log_error(message=str(e), title="Request Permission Error")
		frappe.throw(_(str(e)))


def update_permission_on_grant(customer_number, business_number):
	"""Update permission when customer grants it (called from webhook)"""
	permission = frappe.get_doc("Call Permission", {
		"customer_number": customer_number,
		"business_number": business_number
	})

	permission.permission_status = "Granted"
	permission.granted_at = frappe.utils.now()
	permission.expires_at = frappe.utils.add_days(frappe.utils.now(), 7)
	permission.calls_in_24h = 0
	permission.save()

	frappe.db.commit()


def get_company_whatsapp_number(company):
	"""Helper to get company's WhatsApp number"""
	numbers = frappe.get_all(
		"WhatsApp Number",
		filters={"company": company, "status": "Active"},
		limit=1
	)
	return frappe.get_doc("WhatsApp Number", numbers[0].name) if numbers else None
