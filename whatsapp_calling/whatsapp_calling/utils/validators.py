# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _


def validate_phone_number(phone_number):
	"""
	Validate phone number in E.164 format

	Args:
		phone_number: Phone number string

	Returns:
		tuple: (is_valid, cleaned_number, error_message)
	"""
	if not phone_number:
		return False, None, "Phone number is required"

	# Remove whitespace
	phone_number = phone_number.strip()

	# Check if it starts with +
	if not phone_number.startswith('+'):
		return False, None, "Phone number must start with + (E.164 format)"

	# Remove any spaces, hyphens, or parentheses
	cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)

	# Check if rest are digits
	if not cleaned[1:].isdigit():
		return False, None, "Phone number must contain only digits after +"

	# Check length (E.164 allows 7-15 digits)
	digit_count = len(cleaned[1:])
	if digit_count < 7 or digit_count > 15:
		return False, None, f"Phone number must have 7-15 digits (found {digit_count})"

	return True, cleaned, None


def extract_country_code(phone_number):
	"""
	Extract country code from phone number

	Args:
		phone_number: Phone number in E.164 format (+919876543210)

	Returns:
		str: Country code (e.g., +91)
	"""
	if not phone_number or not phone_number.startswith('+'):
		return None

	# Simple extraction (first 1-3 digits after +)
	# This is simplified - in production use phonenumbers library
	match = re.match(r'\+(\d{1,3})', phone_number)
	if match:
		return f"+{match.group(1)}"

	return None


def validate_whatsapp_number(phone_number):
	"""
	Validate if number is a valid WhatsApp number

	Args:
		phone_number: Phone number string

	Returns:
		tuple: (is_valid, error_message)

	Note: This is a basic validation. For production, you should verify
	the number is actually registered on WhatsApp using the API
	"""
	is_valid, cleaned, error = validate_phone_number(phone_number)

	if not is_valid:
		return False, error

	# Additional WhatsApp-specific validation could go here
	# For example, checking against known invalid patterns

	return True, None


def sanitize_call_id(call_id):
	"""
	Sanitize call ID for database storage

	Args:
		call_id: Raw call ID

	Returns:
		str: Sanitized call ID
	"""
	if not call_id:
		return None

	# Remove any non-alphanumeric characters except hyphens and underscores
	sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', str(call_id))

	return sanitized


def validate_janus_config(config):
	"""
	Validate Janus configuration

	Args:
		config: Dict with janus_url, room_id, etc.

	Returns:
		tuple: (is_valid, error_message)
	"""
	if not config:
		return False, "Configuration is required"

	# Check required fields
	required_fields = ['janus_url', 'room_id']
	for field in required_fields:
		if field not in config:
			return False, f"Missing required field: {field}"

	# Validate URL format
	janus_url = config.get('janus_url')
	if not janus_url.startswith(('http://', 'https://', 'ws://', 'wss://')):
		return False, "Invalid Janus URL format"

	# Validate room_id is numeric
	try:
		int(config.get('room_id'))
	except (ValueError, TypeError):
		return False, "Room ID must be numeric"

	return True, None
