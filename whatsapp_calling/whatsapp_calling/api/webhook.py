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

	# Get settings and stored verify token
	settings = frappe.get_single("WhatsApp Settings")
	stored_token = settings.get_password('webhook_verify_token')

	# Validate token
	if mode == 'subscribe' and token and stored_token and token == stored_token:
		# Return challenge as plain text using download response type
		frappe.response['type'] = 'download'
		frappe.response['filecontent'] = challenge
		frappe.response['filename'] = 'challenge.txt'
		frappe.response['content_type'] = 'text/plain; charset=utf-8'
		frappe.response['display_content_as'] = 'inline'
		return
	else:
		# Log failed verification attempts
		frappe.log_error(
			message=f"Webhook verification failed. Mode: {mode}, Token provided: {bool(token)}, Token stored: {bool(stored_token)}, Match: {token == stored_token if token and stored_token else False}",
			title="Webhook Verification Failed"
		)
		frappe.local.response.http_status_code = 403
		frappe.throw(_("Forbidden"))


def process_webhook():
	"""Process incoming webhook events"""
	try:
		data = json.loads(frappe.request.data)

		# DEBUG: Log raw webhook data
		frappe.logger().info("=" * 80)
		frappe.logger().info("WEBHOOK RECEIVED")
		frappe.logger().info(f"Raw data: {json.dumps(data, indent=2)}")
		frappe.logger().info("=" * 80)

		for entry in data.get("entry", []):
			frappe.logger().info(f"Processing entry: {entry.get('id')}")

			for change in entry.get("changes", []):
				value = change.get("value", {})
				frappe.logger().info(f"Change field: {change.get('field')}")

				# Handle call events
				if "calls" in value:
					frappe.logger().info("CALL EVENT DETECTED")
					frappe.logger().info(f"Call data: {json.dumps(value['calls'][0], indent=2)}")
					frappe.logger().info(f"Metadata: {json.dumps(value.get('metadata', {}), indent=2)}")
					handle_call_event(value["calls"][0], value.get("metadata", {}))

				# Handle message events (for unified thread)
				if "messages" in value:
					frappe.logger().info("MESSAGE EVENT DETECTED")
					handle_message_event(value["messages"][0])

		frappe.logger().info("Webhook processing completed successfully")
		return {"status": "success"}

	except Exception as e:
		frappe.logger().error(f"WEBHOOK PROCESSING ERROR: {str(e)}")
		frappe.logger().exception(e)
		frappe.log_error(message=str(e), title="Webhook Processing Error")
		return {"status": "error"}


def handle_call_event(call_data, metadata):
	"""Process call webhook event"""
	call_id = call_data.get("id")
	status = call_data.get("status")  # ringing, answered, ended
	from_number = call_data.get("from")
	to_number = metadata.get("display_phone_number")
	timestamp = call_data.get("timestamp")

	frappe.logger().info("-" * 80)
	frappe.logger().info("HANDLING CALL EVENT")
	frappe.logger().info(f"Call ID: {call_id}")
	frappe.logger().info(f"Status: {status}")
	frappe.logger().info(f"From: {from_number}")
	frappe.logger().info(f"To: {to_number}")
	frappe.logger().info(f"Timestamp: {timestamp}")
	frappe.logger().info("-" * 80)

	# Get or create call record
	existing = frappe.db.get_value("WhatsApp Call", {"call_id": call_id}, "name")

	if existing:
		frappe.logger().info(f"Found existing call record: {existing}")
		call_doc = frappe.get_doc("WhatsApp Call", existing)
	else:
		frappe.logger().info("Creating new call record...")

		# Get WhatsApp Number details
		try:
			wa_number = frappe.get_doc("WhatsApp Number", {"phone_number": to_number})
			frappe.logger().info(f"Found WhatsApp Number: {wa_number.name}")
		except Exception as e:
			frappe.logger().error(f"ERROR: WhatsApp Number not found for {to_number}")
			frappe.logger().error(f"Error details: {str(e)}")
			frappe.log_error(message=f"WhatsApp Number not found: {to_number}\n{str(e)}", title="Call Event Error")
			return

		# Try to find linked lead
		lead = find_lead_by_mobile(from_number)
		if lead:
			frappe.logger().info(f"Found linked CRM Lead: {lead}")
		else:
			frappe.logger().info("No linked CRM Lead found")

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
		frappe.logger().info(f"✓ Created call record: {call_doc.name}")

	# Update status
	if status == "ringing" and call_doc.direction == "Inbound":
		frappe.logger().info("Status: RINGING - Notifying agents...")
		# Notify available agents
		notify_agents(call_doc)

	elif status == "answered":
		frappe.logger().info("Status: ANSWERED - Updating call record...")
		call_doc.status = "Answered"
		call_doc.answered_at = frappe.utils.now()

	elif status == "ended":
		frappe.logger().info("Status: ENDED - Finalizing call record...")
		call_doc.status = "Ended"
		call_doc.ended_at = frappe.utils.now()
		call_doc.validate()  # Calculate duration and cost

	call_doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.logger().info(f"✓ Call record saved: {call_doc.name} (Status: {call_doc.status})")
	frappe.logger().info("=" * 80)


def find_lead_by_mobile(mobile_number):
	"""Find CRM Lead by mobile number"""
	try:
		# Check if CRM Lead doctype exists (from Frappe CRM module)
		if not frappe.db.exists("DocType", "CRM Lead"):
			return None

		# Clean number for comparison
		clean_number = mobile_number.replace("+", "").replace("-", "").replace(" ", "")

		# CRM Lead uses 'mobile_no' field
		leads = frappe.get_all(
			"CRM Lead",
			filters={
				"mobile_no": ["like", f"%{clean_number[-10:]}%"]  # Match last 10 digits
			},
			limit=1
		)

		return leads[0].name if leads else None
	except Exception as e:
		# If CRM Lead doctype doesn't exist or any other error, just return None
		frappe.log_error(message=str(e), title="Lead Lookup Failed")
		return None


def notify_agents(call_doc):
	"""Send real-time notification to agents"""
	frappe.logger().info("Notifying agents of incoming call...")

	# Find users with access to this company
	users = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User"
		},
		pluck="name"
	)

	frappe.logger().info(f"Found {len(users)} system users to notify")

	notification_count = 0
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
		notification_count += 1
		frappe.logger().info(f"  → Sent notification to user: {user}")

	frappe.logger().info(f"✓ Sent {notification_count} real-time notifications")


def handle_message_event(message_data):
	"""Handle message events (for future unified thread)"""
	# TODO: Implement message handling
	pass
