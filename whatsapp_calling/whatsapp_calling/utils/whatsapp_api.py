# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from urllib.parse import quote


class WhatsAppAPI:
	BASE_URL = "https://graph.facebook.com/v18.0"

	def __init__(self, phone_number_id, access_token):
		self.phone_number_id = phone_number_id
		self.access_token = access_token
		self.headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json"
		}

	def make_call(self, to_number):
		"""
		Initiate outbound call

		Args:
			to_number: Customer's WhatsApp number

		Returns:
			dict with call id and status
		"""
		url = f"{self.BASE_URL}/{self.phone_number_id}/calls"

		payload = {
			"to": to_number,
			"type": "voice"
		}

		response = requests.post(url, json=payload, headers=self.headers, timeout=10)

		if response.status_code == 200:
			return response.json()
		else:
			error_msg = response.json().get("error", {}).get("message", "Unknown error")
			raise Exception(f"WhatsApp API Error: {error_msg}")

	def answer_call(self, call_id, janus_config):
		"""
		Answer incoming call and connect to Janus

		Args:
			call_id: WhatsApp call ID
			janus_config: Dict with janus_url and room_id
		"""
		# Correct WhatsApp API endpoint: POST /{phone_number_id}/calls
		# NOT /calls/{call_id}/answer - call_id goes in the body!
		url = f"{self.BASE_URL}/{self.phone_number_id}/calls"

		payload = {
			"messaging_product": "whatsapp",
			"call_id": call_id,
			"action": "accept",  # Can also be "pre_accept" for faster connection
			"session": {
				"sdp_type": "answer",
				# SDP answer would come from Janus - for now we're just accepting
				"sdp": "v=0\r\no=- 0 0 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\n"
			}
		}

		response = requests.post(url, json=payload, headers=self.headers, timeout=10)

		if response.status_code != 200:
			error_data = response.json().get("error", {})
			error_msg = error_data.get("message", "Unknown error")
			error_code = error_data.get("code", "N/A")
			frappe.log_error(
				message=f"WhatsApp API Error:\nURL: {url}\nStatus: {response.status_code}\nError Code: {error_code}\nMessage: {error_msg}\nPayload: {payload}\nResponse: {response.text}",
				title="Answer Call API Error"
			)
			raise Exception(f"Failed to answer call: {error_msg}")

		return response.json()

	def end_call(self, call_id):
		"""End active call"""
		# Correct WhatsApp API endpoint: POST /{phone_number_id}/calls
		# Call_id goes in the body, not URL path
		url = f"{self.BASE_URL}/{self.phone_number_id}/calls"

		payload = {
			"messaging_product": "whatsapp",
			"call_id": call_id,
			"action": "terminate"
		}

		response = requests.post(url, json=payload, headers=self.headers, timeout=10)

		if response.status_code != 200:
			error_msg = response.json().get("error", {}).get("message", "Unknown error")
			frappe.log_error(
				message=f"End Call Error:\nURL: {url}\nPayload: {payload}\nResponse: {response.text}",
				title="End Call Error"
			)

	def send_template(self, to_number, template_name, components=None):
		"""
		Send WhatsApp template message
		Used for call permission requests
		"""
		url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

		payload = {
			"messaging_product": "whatsapp",
			"to": to_number,
			"type": "template",
			"template": {
				"name": template_name,
				"language": {"code": "en"},
			}
		}

		if components:
			payload["template"]["components"] = components

		response = requests.post(url, json=payload, headers=self.headers, timeout=10)

		if response.status_code != 200:
			error_msg = response.json().get("error", {}).get("message", "Unknown error")
			raise Exception(f"Failed to send template: {error_msg}")

		return response.json()

	def send_message(self, to_number, message_text):
		"""
		Send text message

		Args:
			to_number: Customer's WhatsApp number
			message_text: Text message to send

		Returns:
			dict with message id
		"""
		url = f"{self.BASE_URL}/{self.phone_number_id}/messages"

		payload = {
			"messaging_product": "whatsapp",
			"to": to_number,
			"type": "text",
			"text": {
				"body": message_text
			}
		}

		response = requests.post(url, json=payload, headers=self.headers, timeout=10)

		if response.status_code == 200:
			return response.json()
		else:
			error_msg = response.json().get("error", {}).get("message", "Unknown error")
			raise Exception(f"Failed to send message: {error_msg}")

	def get_media_url(self, media_id):
		"""
		Get media URL from media ID

		Args:
			media_id: Media ID from WhatsApp

		Returns:
			str: Media URL
		"""
		url = f"{self.BASE_URL}/{media_id}"

		response = requests.get(url, headers=self.headers, timeout=10)

		if response.status_code == 200:
			data = response.json()
			return data.get("url")
		else:
			error_msg = response.json().get("error", {}).get("message", "Unknown error")
			raise Exception(f"Failed to get media URL: {error_msg}")

	def download_media(self, media_url, save_path):
		"""
		Download media file from WhatsApp

		Args:
			media_url: URL of the media
			save_path: Path to save the file

		Returns:
			bool: Success status
		"""
		response = requests.get(media_url, headers=self.headers, timeout=30)

		if response.status_code == 200:
			with open(save_path, 'wb') as f:
				f.write(response.content)
			return True
		else:
			return False
