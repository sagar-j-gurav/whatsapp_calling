# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from whatsapp_calling.whatsapp_calling.utils.whatsapp_api import WhatsAppAPI
from whatsapp_calling.whatsapp_calling.api.janus_client import JanusClient
from whatsapp_calling.whatsapp_calling.api.permissions import check_call_permission


@frappe.whitelist()
def make_call(lead_name, mobile_number):
	"""
	Initiate outbound call from CRM Lead

	Args:
		lead_name: Name of CRM Lead
		mobile_number: Customer's mobile number

	Returns:
		dict with call_id and webrtc_config
	"""
	try:
		# Get lead details
		lead = frappe.get_doc("Lead", lead_name)

		# Validate phone number
		if not mobile_number:
			frappe.throw(_("Mobile number is required"))

		# Get company's WhatsApp number
		# For now, get first active number for lead's company
		wa_number = get_company_whatsapp_number(lead.company)

		if not wa_number:
			frappe.throw(_("No WhatsApp number configured for company"))

		# Check call permission
		permission_check = check_call_permission(mobile_number, wa_number.name)
		if not permission_check["can_call"]:
			frappe.throw(_(permission_check["reason"]))

		# Create Janus room first
		janus = JanusClient()
		room_config = janus.setup_call_room()

		# Initialize WhatsApp API call
		wa_api = WhatsAppAPI(
			wa_number.phone_number_id,
			wa_number.get_access_token()
		)

		call_response = wa_api.make_call(mobile_number)

		# Create call record
		call_doc = frappe.get_doc({
			"doctype": "WhatsApp Call",
			"call_id": call_response["id"],
			"customer_number": mobile_number,
			"business_number": wa_number.name,
			"company": lead.company,
			"lead": lead_name,
			"contact_name": lead.lead_name,
			"direction": "Outbound",
			"status": "Initiated",
			"initiated_at": frappe.utils.now(),
			"assigned_to": frappe.session.user,
			"janus_room_id": room_config["room_id"],
			"janus_session_id": room_config["session_id"]
		})
		call_doc.insert()
		frappe.db.commit()

		return {
			"success": True,
			"call_id": call_response["id"],
			"call_name": call_doc.name,
			"webrtc_config": {
				"janus_url": frappe.get_single("WhatsApp Settings").janus_ws_url,
				"room_id": room_config["room_id"],
				"session_id": room_config["session_id"],
				"handle_id": room_config["handle_id"]
			}
		}

	except Exception as e:
		frappe.log_error(message=str(e), title="Make Call Error")
		frappe.throw(_(str(e)))


@frappe.whitelist()
def answer_call(call_id):
	"""
	Answer incoming WhatsApp call

	Args:
		call_id: WhatsApp call ID

	Returns:
		dict with webrtc_config
	"""
	try:
		# Get call record
		call_doc = frappe.get_doc("WhatsApp Call", {"call_id": call_id})

		# Update call record
		call_doc.status = "Answered"
		call_doc.assigned_to = frappe.session.user
		call_doc.answered_at = frappe.utils.now()

		# Create Janus room if not exists
		if not call_doc.janus_room_id:
			janus = JanusClient()
			room_config = janus.setup_call_room()
			call_doc.janus_room_id = room_config["room_id"]
			call_doc.janus_session_id = room_config["session_id"]
		else:
			room_config = {
				"room_id": call_doc.janus_room_id,
				"session_id": call_doc.janus_session_id
			}

		call_doc.save(ignore_permissions=True)

		# Tell WhatsApp to connect to Janus
		wa_number = frappe.get_doc("WhatsApp Number", call_doc.business_number)
		wa_api = WhatsAppAPI(
			wa_number.phone_number_id,
			wa_number.get_access_token()
		)

		# This tells WhatsApp where to send media
		wa_api.answer_call(call_id, {
			"janus_url": frappe.get_single("WhatsApp Settings").janus_ws_url,
			"room_id": call_doc.janus_room_id
		})

		frappe.db.commit()

		return {
			"success": True,
			"webrtc_config": {
				"janus_url": frappe.get_single("WhatsApp Settings").janus_ws_url,
				"room_id": call_doc.janus_room_id,
				"session_id": call_doc.janus_session_id
			}
		}

	except Exception as e:
		frappe.log_error(message=str(e), title="Answer Call Error")
		frappe.throw(_(str(e)))


@frappe.whitelist()
def end_call(call_id):
	"""End active call"""
	try:
		call_doc = frappe.get_doc("WhatsApp Call", {"call_id": call_id})

		# Update status
		call_doc.status = "Ended"
		call_doc.ended_at = frappe.utils.now()
		call_doc.save()

		# Close Janus room
		if call_doc.janus_room_id:
			janus = JanusClient()
			janus.destroy_room(call_doc.janus_session_id, call_doc.janus_room_id)

		# Tell WhatsApp to end call
		wa_number = frappe.get_doc("WhatsApp Number", call_doc.business_number)
		wa_api = WhatsAppAPI(
			wa_number.phone_number_id,
			wa_number.get_access_token()
		)
		wa_api.end_call(call_id)

		frappe.db.commit()

		return {"success": True}

	except Exception as e:
		frappe.log_error(message=str(e), title="End Call Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
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


@frappe.whitelist()
def get_company_whatsapp_number(company):
	"""Get active WhatsApp number for company"""
	numbers = frappe.get_all(
		"WhatsApp Number",
		filters={
			"company": company,
			"status": "Active"
		},
		limit=1
	)

	if numbers:
		return frappe.get_doc("WhatsApp Number", numbers[0].name)
	return None


@frappe.whitelist()
def initiate_call(to_number, lead=None, lead_name=None):
	"""
	Initiate outbound WhatsApp call from CRM Lead

	Args:
		to_number: Customer's mobile number
		lead: CRM Lead ID (optional)
		lead_name: Lead's name for display (optional)

	Returns:
		dict with success status and call details
	"""
	try:
		# Validate phone number
		if not to_number:
			return {"success": False, "error": "Mobile number is required"}

		# Get first active WhatsApp number
		# TODO: Allow selection of which business number to use
		wa_numbers = frappe.get_all(
			"WhatsApp Number",
			filters={"status": "Active"},
			limit=1
		)

		if not wa_numbers:
			return {"success": False, "error": "No active WhatsApp number configured"}

		wa_number = frappe.get_doc("WhatsApp Number", wa_numbers[0].name)

		# Check call permission
		permission_check = check_call_permission(to_number, wa_number.name)
		if not permission_check["can_call"]:
			return {"success": False, "error": permission_check["reason"]}

		# Create Janus room first
		janus = JanusClient()
		room_config = janus.setup_call_room()

		# Initialize WhatsApp API call
		wa_api = WhatsAppAPI(
			wa_number.phone_number_id,
			wa_number.get_password('access_token')
		)

		call_response = wa_api.make_call(to_number)

		# Create call record
		call_doc = frappe.get_doc({
			"doctype": "WhatsApp Call",
			"call_id": call_response["id"],
			"customer_number": to_number,
			"business_number": wa_number.name,
			"company": wa_number.company,
			"lead": lead,
			"contact_name": lead_name,
			"direction": "Outbound",
			"status": "Initiated",
			"initiated_at": frappe.utils.now(),
			"assigned_to": frappe.session.user,
			"janus_room_id": room_config["room_id"],
			"janus_session_id": room_config["session_id"]
		})
		call_doc.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"call_id": call_response["id"],
			"call_name": call_doc.name,
			"webrtc_config": {
				"janus_url": frappe.get_single("WhatsApp Settings").janus_ws_url,
				"room_id": room_config["room_id"],
				"session_id": room_config["session_id"],
				"handle_id": room_config.get("handle_id")
			}
		}

	except Exception as e:
		frappe.log_error(message=str(e), title="Initiate Call Error")
		return {"success": False, "error": str(e)}
