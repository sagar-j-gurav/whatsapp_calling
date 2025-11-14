# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _


@frappe.whitelist(allow_guest=True, methods=['GET', 'POST'])
def whatsapp_webhook():
	"""
	WhatsApp Cloud API webhook endpoint

	GET: Verification from Meta
	POST: Event notifications (calls, messages)
	"""
	try:
		if frappe.request.method == "GET":
			return verify_webhook()
		else:
			return process_webhook()
	except Exception as e:
		frappe.log_error(message=str(e), title="WhatsApp Webhook Error")
		return {"status": "error", "message": str(e)}


def verify_webhook():
	"""Verify webhook with Meta"""
	mode = frappe.form_dict.get('hub.mode')
	token = frappe.form_dict.get('hub.verify_token')
	challenge = frappe.form_dict.get('hub.challenge')

	settings = frappe.get_single("WhatsApp Settings")

	if mode == 'subscribe' and token == settings.get_password('webhook_verify_token'):
		# Return challenge as plain text, not JSON
		frappe.local.response.http_status_code = 200
		frappe.local.response.type = "text"
		frappe.local.response.data = challenge
		return
	else:
		frappe.local.response.http_status_code = 403
		frappe.throw(_("Forbidden"))


def process_webhook():
	"""Process incoming webhook events"""
	try:
		data = json.loads(frappe.request.data)

		for entry in data.get("entry", []):
			for change in entry.get("changes", []):
				value = change.get("value", {})

				# Handle call events
				if "calls" in value:
					handle_call_event(value["calls"][0], value.get("metadata", {}))

				# Handle message events (for unified thread)
				if "messages" in value:
					handle_message_event(value["messages"][0])

		return {"status": "success"}

	except Exception as e:
		frappe.log_error(message=str(e), title="Webhook Processing Error")
		return {"status": "error"}


def handle_call_event(call_data, metadata):
	"""Process call webhook event"""
	call_id = call_data.get("id")
	status = call_data.get("status")  # ringing, answered, ended
	from_number = call_data.get("from")
	to_number = metadata.get("display_phone_number")
	timestamp = call_data.get("timestamp")

	# Get or create call record
	existing = frappe.db.get_value("WhatsApp Call", {"call_id": call_id}, "name")

	if existing:
		call_doc = frappe.get_doc("WhatsApp Call", existing)
	else:
		# New inbound call
		# Get WhatsApp Number details
		wa_number = frappe.get_doc("WhatsApp Number", {"phone_number": to_number})

		# Try to find linked lead
		lead = find_lead_by_mobile(from_number)

		call_doc = frappe.get_doc({
			"doctype": "WhatsApp Call",
			"call_id": call_id,
			"customer_number": from_number,
			"business_number": wa_number.name,
			"company": wa_number.company,
			"direction": "Inbound",
			"status": "Ringing",
			"initiated_at": frappe.utils.now(),
			"lead": lead
		})
		call_doc.insert(ignore_permissions=True)

	# Update status
	if status == "ringing" and call_doc.direction == "Inbound":
		# Notify available agents
		notify_agents(call_doc)

	elif status == "answered":
		call_doc.status = "Answered"
		call_doc.answered_at = frappe.utils.now()

	elif status == "ended":
		call_doc.status = "Ended"
		call_doc.ended_at = frappe.utils.now()
		call_doc.validate()  # Calculate duration and cost

	call_doc.save(ignore_permissions=True)
	frappe.db.commit()


def find_lead_by_mobile(mobile_number):
	"""Find CRM Lead by mobile number"""
	# Clean number for comparison
	clean_number = mobile_number.replace("+", "").replace("-", "").replace(" ", "")

	leads = frappe.get_all(
		"Lead",
		filters={
			"mobile_no": ["like", f"%{clean_number[-10:]}%"]  # Match last 10 digits
		},
		limit=1
	)

	return leads[0].name if leads else None


def notify_agents(call_doc):
	"""Send real-time notification to agents"""
	# Find users with access to this company
	users = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User"
		},
		pluck="name"
	)

	for user in users:
		# Check if user has permission for this company
		# TODO: Implement proper permission check

		frappe.publish_realtime(
			event='incoming_whatsapp_call',
			message={
				'call_id': call_doc.call_id,
				'call_name': call_doc.name,
				'customer_number': call_doc.customer_number,
				'customer_name': call_doc.contact_name or "Unknown",
				'lead': call_doc.lead
			},
			user=user
		)


def handle_message_event(message_data):
	"""Handle message events (for future unified thread)"""
	# TODO: Implement message handling
	pass
