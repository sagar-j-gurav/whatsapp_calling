# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta
import os


def cleanup_old_recordings():
	"""
	Scheduled task: Delete old call recordings based on retention policy
	Runs hourly
	"""
	try:
		settings = frappe.get_single("WhatsApp Settings")

		if not settings.enable_call_recording or settings.retention_days == 0:
			return  # No cleanup needed

		# Calculate cutoff date
		cutoff_date = frappe.utils.add_days(frappe.utils.now(), -settings.retention_days)

		# Find old calls with recordings
		old_calls = frappe.get_all(
			"WhatsApp Call",
			filters={
				"ended_at": ["<", cutoff_date],
				"recording_file": ["is", "set"]
			},
			fields=["name", "recording_file"]
		)

		deleted_count = 0
		for call in old_calls:
			try:
				# Delete the recording file
				if call.recording_file:
					file_path = frappe.get_site_path() + call.recording_file
					if os.path.exists(file_path):
						os.remove(file_path)

				# Update call record
				frappe.db.set_value("WhatsApp Call", call.name, {
					"recording_file": None,
					"recording_url": None
				})

				deleted_count += 1

			except Exception as e:
				frappe.log_error(f"Failed to delete recording for {call.name}: {str(e)}")

		if deleted_count > 0:
			frappe.db.commit()
			frappe.logger().info(f"Deleted {deleted_count} old call recordings")

	except Exception as e:
		frappe.log_error(message=str(e), title="Cleanup Old Recordings Error")


def check_expired_permissions():
	"""
	Scheduled task: Check and update expired call permissions
	Runs daily
	"""
	try:
		# Find granted permissions that have expired
		expired_permissions = frappe.get_all(
			"Call Permission",
			filters={
				"permission_status": "Granted",
				"expires_at": ["<", frappe.utils.now()]
			},
			pluck="name"
		)

		for permission_name in expired_permissions:
			permission = frappe.get_doc("Call Permission", permission_name)
			permission.permission_status = "Expired"
			permission.save(ignore_permissions=True)

		if expired_permissions:
			frappe.db.commit()
			frappe.logger().info(f"Marked {len(expired_permissions)} permissions as expired")

	except Exception as e:
		frappe.log_error(message=str(e), title="Check Expired Permissions Error")


def reset_daily_counters():
	"""
	Scheduled task: Reset daily call counters
	Runs daily at midnight
	"""
	try:
		# Reset calls_in_24h for permissions where last_call_at is more than 24h ago
		cutoff_time = frappe.utils.add_hours(frappe.utils.now(), -24)

		permissions = frappe.get_all(
			"Call Permission",
			filters={
				"last_call_at": ["<", cutoff_time],
				"calls_in_24h": [">", 0]
			},
			pluck="name"
		)

		for permission_name in permissions:
			frappe.db.set_value("Call Permission", permission_name, "calls_in_24h", 0)

		if permissions:
			frappe.db.commit()
			frappe.logger().info(f"Reset daily counters for {len(permissions)} permissions")

	except Exception as e:
		frappe.log_error(message=str(e), title="Reset Daily Counters Error")


def update_monthly_usage():
	"""
	Scheduled task: Reset monthly usage counters on 1st of each month
	Runs daily (checks if it's the 1st)
	"""
	try:
		from datetime import date

		today = date.today()

		# Only run on 1st of the month
		if today.day != 1:
			return

		# Reset current_month_usage for all WhatsApp Numbers
		wa_numbers = frappe.get_all("WhatsApp Number", pluck="name")

		for wa_number in wa_numbers:
			frappe.db.set_value("WhatsApp Number", wa_number, "current_month_usage", 0)

		frappe.db.commit()
		frappe.logger().info("Reset monthly usage for all WhatsApp numbers")

	except Exception as e:
		frappe.log_error(message=str(e), title="Update Monthly Usage Error")


def cleanup_stale_janus_rooms():
	"""
	Scheduled task: Cleanup Janus rooms that are stuck in limbo
	Runs hourly
	"""
	try:
		from whatsapp_calling.whatsapp_calling.api.janus_client import JanusClient

		# Find calls that ended more than 1 hour ago but still have Janus room
		cutoff_time = frappe.utils.add_hours(frappe.utils.now(), -1)

		stale_calls = frappe.get_all(
			"WhatsApp Call",
			filters={
				"status": "Ended",
				"ended_at": ["<", cutoff_time],
				"janus_room_id": ["is", "set"]
			},
			fields=["name", "janus_session_id", "janus_room_id"]
		)

		janus = JanusClient()
		cleaned_count = 0

		for call in stale_calls:
			try:
				# Try to destroy the Janus room
				janus.destroy_room(call.janus_session_id, call.janus_room_id)

				# Clear Janus room info from call
				frappe.db.set_value("WhatsApp Call", call.name, {
					"janus_room_id": None,
					"janus_session_id": None
				})

				cleaned_count += 1

			except Exception as e:
				# Log but continue with other rooms
				frappe.log_error(f"Failed to cleanup Janus room for {call.name}: {str(e)}")

		if cleaned_count > 0:
			frappe.db.commit()
			frappe.logger().info(f"Cleaned up {cleaned_count} stale Janus rooms")

	except Exception as e:
		frappe.log_error(message=str(e), title="Cleanup Stale Janus Rooms Error")


def update_call_statistics():
	"""
	Scheduled task: Update call statistics and analytics
	Runs daily
	"""
	try:
		# This is a placeholder for future analytics features
		# You can implement aggregation of call data here

		# Example: Calculate daily call volumes
		today_start = frappe.utils.today()

		call_stats = frappe.db.sql("""
			SELECT
				company,
				COUNT(*) as total_calls,
				SUM(CASE WHEN status = 'Answered' THEN 1 ELSE 0 END) as answered_calls,
				SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed_calls,
				SUM(duration_seconds) as total_duration,
				SUM(cost) as total_cost
			FROM `tabWhatsApp Call`
			WHERE DATE(initiated_at) = %s
			GROUP BY company
		""", (today_start,), as_dict=True)

		# Log statistics
		for stat in call_stats:
			frappe.logger().info(
				f"Call stats for {stat.company}: "
				f"{stat.total_calls} calls, "
				f"{stat.answered_calls} answered, "
				f"{stat.total_duration}s duration, "
				f"₹{stat.total_cost} cost"
			)

		# You could save these to a separate DocType for historical tracking

	except Exception as e:
		frappe.log_error(message=str(e), title="Update Call Statistics Error")


def send_daily_summary_email():
	"""
	Scheduled task: Send daily summary email to system managers
	Runs daily at 9 AM
	"""
	try:
		from frappe.utils.email_lib import sendmail_to_system_managers

		# Calculate yesterday's stats
		yesterday = frappe.utils.add_days(frappe.utils.today(), -1)

		stats = frappe.db.sql("""
			SELECT
				COUNT(*) as total_calls,
				SUM(CASE WHEN status = 'Answered' THEN 1 ELSE 0 END) as answered_calls,
				SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed_calls,
				SUM(duration_seconds) as total_duration,
				SUM(cost) as total_cost
			FROM `tabWhatsApp Call`
			WHERE DATE(initiated_at) = %s
		""", (yesterday,), as_dict=True)[0]

		if stats.total_calls == 0:
			return  # No calls yesterday

		# Format duration
		hours = stats.total_duration // 3600
		minutes = (stats.total_duration % 3600) // 60

		message = f"""
		<h3>WhatsApp Calling Daily Summary - {yesterday}</h3>

		<table style="border-collapse: collapse; width: 100%; max-width: 600px;">
			<tr style="background-color: #f2f2f2;">
				<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Metric</th>
				<th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Value</th>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Total Calls</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">{stats.total_calls}</td>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Answered Calls</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">{stats.answered_calls}</td>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Failed Calls</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">{stats.failed_calls}</td>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Total Duration</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">{hours}h {minutes}m</td>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Total Cost</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">₹{stats.total_cost:.2f}</td>
			</tr>
			<tr>
				<td style="padding: 12px; border: 1px solid #ddd;">Answer Rate</td>
				<td style="padding: 12px; text-align: right; border: 1px solid #ddd;">
					{(stats.answered_calls / stats.total_calls * 100):.1f}%
				</td>
			</tr>
		</table>
		"""

		sendmail_to_system_managers(
			subject=f"WhatsApp Calling Daily Summary - {yesterday}",
			message=message
		)

	except Exception as e:
		frappe.log_error(message=str(e), title="Send Daily Summary Email Error")
