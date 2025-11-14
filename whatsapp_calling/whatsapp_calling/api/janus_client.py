# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
import requests
import secrets
import json


class JanusClient:
	def __init__(self):
		settings = frappe.get_single("WhatsApp Settings")
		self.base_url = settings.janus_http_url
		self.api_secret = settings.get_password('janus_api_secret')
		self.session_id = None
		self.handle_id = None

	def setup_call_room(self):
		"""
		Setup complete Janus room for a call

		Returns:
			dict with session_id, handle_id, room_id
		"""
		# Create session
		self.session_id = self.create_session()

		# Attach AudioBridge plugin
		self.handle_id = self.attach_plugin(self.session_id)

		# Create room
		room_id = self.create_room(self.session_id, self.handle_id)

		return {
			"session_id": self.session_id,
			"handle_id": self.handle_id,
			"room_id": room_id
		}

	def create_session(self):
		"""Create Janus session"""
		url = f"{self.base_url}"

		payload = {
			"janus": "create",
			"transaction": self._generate_transaction_id()
		}

		if self.api_secret:
			payload["apisecret"] = self.api_secret

		response = requests.post(url, json=payload, timeout=10)
		response.raise_for_status()

		data = response.json()

		if data.get("janus") == "success":
			return str(data["data"]["id"])
		else:
			raise Exception(f"Failed to create Janus session: {data}")

	def attach_plugin(self, session_id, plugin="janus.plugin.audiobridge"):
		"""Attach AudioBridge plugin"""
		url = f"{self.base_url}/{session_id}"

		payload = {
			"janus": "attach",
			"plugin": plugin,
			"transaction": self._generate_transaction_id()
		}

		if self.api_secret:
			payload["apisecret"] = self.api_secret

		response = requests.post(url, json=payload, timeout=10)
		response.raise_for_status()

		data = response.json()

		if data.get("janus") == "success":
			return str(data["data"]["id"])
		else:
			raise Exception(f"Failed to attach plugin: {data}")

	def create_room(self, session_id, handle_id, room_id=None):
		"""Create audio mixing room"""
		url = f"{self.base_url}/{session_id}/{handle_id}"

		if not room_id:
			room_id = secrets.randbelow(999999)

		settings = frappe.get_single("WhatsApp Settings")

		payload = {
			"janus": "message",
			"transaction": self._generate_transaction_id(),
			"body": {
				"request": "create",
				"room": room_id,
				"description": f"WhatsApp Call Room {room_id}",
				"sampling_rate": 48000,  # WhatsApp uses 48kHz
				"record": settings.enable_call_recording,
				"rec_dir": settings.recording_storage_path if settings.enable_call_recording else None
			}
		}

		if self.api_secret:
			payload["apisecret"] = self.api_secret

		response = requests.post(url, json=payload, timeout=10)
		response.raise_for_status()

		data = response.json()

		if data.get("janus") == "success" or data.get("plugindata", {}).get("data", {}).get("audiobridge") == "created":
			return str(room_id)
		else:
			raise Exception(f"Failed to create room: {data}")

	def destroy_room(self, session_id, room_id):
		"""Destroy room and cleanup"""
		try:
			url = f"{self.base_url}/{session_id}/{self.handle_id}"

			payload = {
				"janus": "message",
				"transaction": self._generate_transaction_id(),
				"body": {
					"request": "destroy",
					"room": room_id
				}
			}

			if self.api_secret:
				payload["apisecret"] = self.api_secret

			requests.post(url, json=payload, timeout=5)

			# Destroy session
			url = f"{self.base_url}/{session_id}"
			payload = {
				"janus": "destroy",
				"transaction": self._generate_transaction_id()
			}
			if self.api_secret:
				payload["apisecret"] = self.api_secret

			requests.post(url, json=payload, timeout=5)

		except Exception as e:
			frappe.log_error(message=str(e), title="Janus Cleanup Error")

	def negotiate_sdp(self, sdp_offer):
		"""
		Negotiate SDP with Janus for incoming WhatsApp call

		Args:
			sdp_offer: SDP offer string from WhatsApp webhook

		Returns:
			dict with session_id, handle_id, sdp_answer
		"""
		print("=== Starting Janus SDP Negotiation ===")

		# Create session
		session_id = self.create_session()
		print(f"✓ Created Janus session: {session_id}")

		# Attach VideoCall plugin for peer-to-peer SDP negotiation
		handle_id = self.attach_plugin(session_id, plugin="janus.plugin.videocall")
		print(f"✓ Attached VideoCall plugin: {handle_id}")

		# Send SDP offer to Janus and get answer
		url = f"{self.base_url}/{session_id}/{handle_id}"

		payload = {
			"janus": "message",
			"transaction": self._generate_transaction_id(),
			"body": {
				"request": "call",
				"username": f"whatsapp_call_{secrets.token_hex(4)}"
			},
			"jsep": {
				"type": "offer",
				"sdp": sdp_offer
			}
		}

		if self.api_secret:
			payload["apisecret"] = self.api_secret

		print(f"Sending SDP offer to Janus (first 100 chars): {sdp_offer[:100]}...")
		response = requests.post(url, json=payload, timeout=10)
		response.raise_for_status()

		data = response.json()
		print(f"Janus response: {json.dumps(data, indent=2)}")

		# Extract SDP answer from response
		if "jsep" in data and data["jsep"]["type"] == "answer":
			sdp_answer = data["jsep"]["sdp"]
			print(f"✓ Received SDP answer from Janus (first 100 chars): {sdp_answer[:100]}...")

			return {
				"session_id": session_id,
				"handle_id": handle_id,
				"sdp_answer": sdp_answer
			}
		else:
			# Sometimes Janus sends answer in a follow-up event
			# Need to poll for it or handle async event
			frappe.log_error(
				message=f"No SDP answer in immediate response. Data: {json.dumps(data, indent=2)}",
				title="Janus SDP Negotiation - No Answer"
			)
			raise Exception("No SDP answer received from Janus")

	def _generate_transaction_id(self):
		"""Generate random transaction ID"""
		return secrets.token_hex(12)
