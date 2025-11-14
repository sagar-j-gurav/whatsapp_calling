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

		# DEBUG: Log to Error Log so we can see it
		frappe.log_error(
			message=f"WEBHOOK RECEIVED:\n{json.dumps(data, indent=2)}",
			title="WhatsApp Webhook Debug"
		)

		# Also print to console
		print("=" * 80)
		print("WEBHOOK RECEIVED")
		print(f"Raw data: {json.dumps(data, indent=2)}")
		print("=" * 80)

		for entry in data.get("entry", []):
			print(f"Processing entry: {entry.get('id')}")

			for change in entry.get("changes", []):
				value = change.get("value", {})
				print(f"Change field: {change.get('field')}")

				# Handle call events
				if "calls" in value:
					print("CALL EVENT DETECTED")
					print(f"Call data: {json.dumps(value['calls'][0], indent=2)}")
					print(f"Metadata: {json.dumps(value.get('metadata', {}), indent=2)}")

					frappe.log_error(
						message=f"CALL EVENT:\nCall: {json.dumps(value['calls'][0], indent=2)}\nMetadata: {json.dumps(value.get('metadata', {}), indent=2)}",
						title="WhatsApp Call Event Debug"
					)

					# Extract WhatsApp profile name from contacts
					contacts = value.get("contacts", [])
					wa_profile_name = None
					if contacts and len(contacts) > 0:
						profile = contacts[0].get("profile", {})
						wa_profile_name = profile.get("name")
						print(f"WhatsApp Profile Name: {wa_profile_name}")

					handle_call_event(value["calls"][0], value.get("metadata", {}), wa_profile_name)

				# Handle message events (for unified thread)
				if "messages" in value:
					print("MESSAGE EVENT DETECTED")
					handle_message_event(value["messages"][0])

		print("Webhook processing completed successfully")
		frappe.log_error(
			message="Webhook processing completed successfully",
			title="WhatsApp Webhook Success"
		)
		return {"status": "success"}

	except Exception as e:
		print(f"WEBHOOK PROCESSING ERROR: {str(e)}")
		import traceback
		traceback.print_exc()
		frappe.log_error(
			message=f"WEBHOOK ERROR:\n{str(e)}\n\n{traceback.format_exc()}",
			title="WhatsApp Webhook Error"
		)
		return {"status": "error"}


def handle_call_event(call_data, metadata, wa_profile_name=None):
	"""Process call webhook event"""
	call_id = call_data.get("id")
	event = call_data.get("event")  # connect, terminate
	status = call_data.get("status")  # COMPLETED, etc
	from_number = call_data.get("from")
	to_number = metadata.get("display_phone_number")
	timestamp = call_data.get("timestamp")

	# Extract SDP session data for incoming calls
	session = call_data.get("session", {})
	sdp_offer = session.get("sdp")
	sdp_type = session.get("sdp_type")

	print("-" * 80)
	print("HANDLING CALL EVENT")
	print(f"Call ID: {call_id}")
	print(f"Event: {event}")
	print(f"Status: {status}")
	print(f"From: {from_number}")
	print(f"To: {to_number}")
	print(f"Timestamp: {timestamp}")
	if sdp_offer:
		print(f"SDP Type: {sdp_type}")
		print(f"SDP Offer (first 100 chars): {sdp_offer[:100]}...")
	print("-" * 80)

	# Get or create call record
	existing = frappe.db.get_value("WhatsApp Call", {"call_id": call_id}, "name")

	# Initialize lead_name for use later
	lead_name = None

	if existing:
		print(f"Found existing call record: {existing}")
		call_doc = frappe.get_doc("WhatsApp Call", existing)

		# Extract lead name from existing call record
		if call_doc.lead:
			try:
				lead_doc = frappe.get_doc("CRM Lead", call_doc.lead)
				lead_name = lead_doc.lead_name or lead_doc.first_name
				print(f"Existing call - Lead name: {lead_name}")
			except:
				pass
	else:
		print("Creating new call record...")

		# Get WhatsApp Number details
		# Normalize phone number - webhook sends without +, but we store with +
		try:
			# First try exact match
			wa_number = frappe.db.get_value(
				"WhatsApp Number",
				{"phone_number": to_number},
				["name"],
				as_dict=True
			)

			# If not found, try with + prefix
			if not wa_number:
				wa_number = frappe.db.get_value(
					"WhatsApp Number",
					{"phone_number": f"+{to_number}"},
					["name"],
					as_dict=True
				)

			if not wa_number:
				raise frappe.exceptions.DoesNotExistError(f"WhatsApp Number not found for {to_number} or +{to_number}")

			wa_number = frappe.get_doc("WhatsApp Number", wa_number.name)
			print(f"Found WhatsApp Number: {wa_number.name}")
		except Exception as e:
			error_msg = f"ERROR: WhatsApp Number not found for {to_number} or +{to_number}\nError: {str(e)}"
			print(error_msg)
			import traceback
			traceback.print_exc()
			frappe.log_error(
				message=f"{error_msg}\n\n{traceback.format_exc()}",
				title="WhatsApp Number Not Found"
			)
			return

		# Try to find linked lead
		lead = find_lead_by_mobile(from_number)
		lead_name = None
		if lead:
			print(f"Found linked CRM Lead: {lead}")
			# Get lead name
			lead_doc = frappe.get_doc("CRM Lead", lead)
			lead_name = lead_doc.lead_name or lead_doc.first_name
			print(f"Lead name: {lead_name}")
		else:
			print("No linked CRM Lead found")

		# Determine contact name - prefer lead name, fallback to WhatsApp profile name
		contact_name = lead_name or wa_profile_name
		print(f"Contact name for call: {contact_name}")

		try:
			call_doc = frappe.get_doc({
				"doctype": "WhatsApp Call",
				"call_id": call_id,
				"customer_number": from_number,
				"business_number": wa_number.name,
				"company": wa_number.company,
				"direction": "Inbound",
				"status": "Ringing",
				"initiated_at": frappe.utils.now(),
				"lead": lead,
				"contact_name": contact_name,
				"sdp_offer": sdp_offer  # Add SDP offer during document creation
			})

			call_doc.insert(ignore_permissions=True)
			print(f"✓ Created call record: {call_doc.name}")

			# Verify SDP offer was saved
			if sdp_offer:
				saved_sdp = frappe.db.get_value("WhatsApp Call", call_doc.name, "sdp_offer")
				if saved_sdp:
					print(f"✓ Verified SDP offer saved (length: {len(saved_sdp)} chars)")
				else:
					print(f"WARNING: SDP offer not saved! Attempting to save again...")
					# Try using db_set as fallback
					call_doc.db_set("sdp_offer", sdp_offer, update_modified=False)
					frappe.db.commit()
					print(f"✓ Stored SDP offer using db_set")

			frappe.log_error(
				message=f"Call record created successfully:\nID: {call_doc.name}\nCall ID: {call_id}\nFrom: {from_number}\nTo: {to_number}",
				title="WhatsApp Call Created"
			)
		except Exception as e:
			error_msg = f"ERROR creating call record: {str(e)}"
			print(error_msg)
			import traceback
			traceback.print_exc()
			frappe.log_error(
				message=f"{error_msg}\n\n{traceback.format_exc()}\n\nData:\nCall ID: {call_id}\nFrom: {from_number}\nTo: {to_number}",
				title="Call Record Creation Failed"
			)
			return

	# Update status based on event type
	if event == "connect":
		print("Event: CONNECT - Call initiated, notifying agents...")
		if call_doc.status != "Ringing":
			call_doc.status = "Ringing"
		# Notify available agents with lead_name and wa_profile_name for display
		print(f"Notifying agents - lead_name: {lead_name}, wa_profile_name: {wa_profile_name}")
		notify_agents(
			call_doc,
			lead_name=lead_name,
			wa_profile_name=wa_profile_name
		)

	elif event == "answer":
		print("Event: ANSWER - Call answered...")
		call_doc.status = "Answered"
		call_doc.answered_at = frappe.utils.now()

	elif event == "terminate":
		print("Event: TERMINATE - Call ended...")
		call_doc.status = "Ended"
		call_doc.ended_at = frappe.utils.now()
		# Calculate duration
		if call_doc.initiated_at and call_doc.ended_at:
			from frappe.utils import get_datetime
			initiated = get_datetime(call_doc.initiated_at)
			ended = get_datetime(call_doc.ended_at)
			duration = (ended - initiated).total_seconds()
			call_doc.duration_seconds = int(duration)
			print(f"  Duration: {duration} seconds")

	call_doc.save(ignore_permissions=True)
	frappe.db.commit()
	print(f"✓ Call record saved: {call_doc.name} (Status: {call_doc.status})")
	print("=" * 80)


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


def notify_agents(call_doc, lead_name=None, wa_profile_name=None):
	"""Send real-time notification to agents"""
	print("=" * 80)
	print("NOTIFY_AGENTS - Starting...")
	print(f"Call Doc: {call_doc.name}")
	print(f"Lead Name (passed): {lead_name}")
	print(f"WA Profile Name (passed): {wa_profile_name}")

	# If lead_name not provided, try to get it from the lead
	if not lead_name and call_doc.lead:
		try:
			lead_doc = frappe.get_doc("CRM Lead", call_doc.lead)
			lead_name = lead_doc.lead_name or lead_doc.first_name
			print(f"Lead Name (extracted from call_doc.lead): {lead_name}")
		except:
			pass

	# Find users with access to this company
	users = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User"
		},
		pluck="name"
	)

	print(f"Found {len(users)} system users to notify: {users}")

	# Prepare message data
	message_data = {
		'call_id': call_doc.call_id,
		'call_name': call_doc.name,
		'customer_number': call_doc.customer_number,
		'customer_name': call_doc.contact_name or "Unknown",
		'lead': call_doc.lead,
		'lead_name': lead_name,  # Lead name from CRM
		'wa_profile_name': wa_profile_name  # WhatsApp profile name
	}
	print(f"Message data to send: {message_data}")

	notification_count = 0
	for user in users:
		# Check if user has permission for this company
		# TODO: Implement proper permission check

		print(f"Publishing realtime event 'incoming_whatsapp_call' to user: {user}")
		frappe.publish_realtime(
			event='incoming_whatsapp_call',
			message=message_data,
			user=user
		)
		notification_count += 1
		print(f"  ✓ Sent notification to user: {user}")

	print(f"✓ Sent {notification_count} real-time notifications")
	print("=" * 80)


def handle_message_event(message_data):
	"""Handle message events (for future unified thread)"""
	# TODO: Implement message handling
	pass
