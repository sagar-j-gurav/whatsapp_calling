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
		Negotiate SDP with Janus AudioBridge for incoming WhatsApp call

		Args:
			sdp_offer: SDP offer string from WhatsApp webhook

		Returns:
			dict with session_id, handle_id, room_id, sdp_answer
		"""
		print("=== Starting Janus SDP Negotiation (AudioBridge) ===")

		# Create session
		session_id = self.create_session()
		print(f"✓ Created Janus session: {session_id}")

		# Attach AudioBridge plugin
		handle_id = self.attach_plugin(session_id, plugin="janus.plugin.audiobridge")
		print(f"✓ Attached AudioBridge plugin: {handle_id}")

		# Create a room for this call
		room_id = secrets.randbelow(999999)
		url = f"{self.base_url}/{session_id}/{handle_id}"

		# Step 1: Create AudioBridge room
		create_payload = {
			"janus": "message",
			"transaction": self._generate_transaction_id(),
			"body": {
				"request": "create",
				"room": room_id,
				"description": f"WhatsApp Call Room {room_id}",
				"sampling_rate": 48000,  # WhatsApp uses 48kHz
				"audiolevel_event": False
			}
		}
		if self.api_secret:
			create_payload["apisecret"] = self.api_secret

		print(f"Creating AudioBridge room {room_id}...")
		response = requests.post(url, json=create_payload, timeout=10)
		response.raise_for_status()
		print(f"✓ Room created: {room_id}")

		# Step 2: Join the room with WhatsApp's SDP offer
		join_payload = {
			"janus": "message",
			"transaction": self._generate_transaction_id(),
			"body": {
				"request": "join",
				"room": room_id,
				"display": "WhatsApp Caller"
			},
			"jsep": {
				"type": "offer",
				"sdp": sdp_offer
			}
		}
		if self.api_secret:
			join_payload["apisecret"] = self.api_secret

		print(f"Joining room with SDP offer (first 100 chars): {sdp_offer[:100]}...")
		response = requests.post(url, json=join_payload, timeout=10)
		response.raise_for_status()

		data = response.json()
		print(f"Janus join response: {json.dumps(data, indent=2)}")

		# Check if we got an immediate answer
		if "jsep" in data and data["jsep"]["type"] == "answer":
			sdp_answer = data["jsep"]["sdp"]
			print(f"✓ Received SDP answer immediately")
			print(f"  SDP Answer (first 100 chars): {sdp_answer[:100]}...")

			return {
				"session_id": session_id,
				"handle_id": handle_id,
				"room_id": room_id,
				"sdp_answer": sdp_answer
			}

		# Janus sent an "ack" - need to poll for events to get the answer
		if data.get("janus") == "ack":
			print("Janus sent 'ack', polling for SDP answer event...")

			# Poll for events (max 5 seconds, check every 100ms)
			import time
			max_attempts = 50
			for attempt in range(max_attempts):
				time.sleep(0.1)  # Wait 100ms between polls

				# Get events from Janus session
				events_url = f"{self.base_url}/{session_id}?maxev=1"
				event_response = requests.get(events_url, timeout=5)

				if event_response.status_code == 200:
					event_data = event_response.json()
					print(f"Poll attempt {attempt + 1}: {event_data.get('janus', 'no janus field')}")

					# Check if this event has the JSEP answer
					if "jsep" in event_data and event_data["jsep"]["type"] == "answer":
						sdp_answer = event_data["jsep"]["sdp"]
						print(f"✓ Received SDP answer from event after {attempt + 1} attempts")
						print(f"  SDP Answer (first 100 chars): {sdp_answer[:100]}...")

						return {
							"session_id": session_id,
							"handle_id": handle_id,
							"room_id": room_id,
							"sdp_answer": sdp_answer
						}

			# Timeout - no answer received
			frappe.log_error(
				message=f"Polled {max_attempts} times but no SDP answer received",
				title="Janus SDP Negotiation - Timeout"
			)
			raise Exception("Timeout waiting for SDP answer from Janus")

		# Unexpected response
		frappe.log_error(
			message=f"Unexpected Janus response. Data: {json.dumps(data, indent=2)}",
			title="Janus SDP Negotiation - Unexpected Response"
		)
		raise Exception("Unexpected response from Janus")

	def _generate_transaction_id(self):
		"""Generate random transaction ID"""
		return secrets.token_hex(12)
