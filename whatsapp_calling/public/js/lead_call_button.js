// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lead', {
	refresh: function(frm) {
		// Only show if lead has mobile number
		if (frm.doc.mobile_no && !frm.is_new()) {
			add_whatsapp_call_buttons(frm);
		}
	}
});

function add_whatsapp_call_buttons(frm) {
	// Clear existing buttons to avoid duplicates
	frm.custom_buttons = {};

	// Add WhatsApp Call button
	frm.add_custom_button(__('WhatsApp Call'), function() {
		initiate_whatsapp_call(frm);
	}, __('📞'));

	// Add Request Permission button
	frm.add_custom_button(__('Request Call Permission'), function() {
		request_call_permission(frm);
	}, __('📞'));

	// Add View Call History button
	frm.add_custom_button(__('View Call History'), function() {
		view_call_history(frm);
	}, __('📞'));

	// Style the WhatsApp Call button with WhatsApp colors
	setTimeout(() => {
		$('button:contains("WhatsApp Call")').css({
			'background-color': '#25D366',
			'color': 'white',
			'border-color': '#25D366'
		}).hover(
			function() {
				$(this).css({
					'background-color': '#128C7E',
					'border-color': '#128C7E'
				});
			},
			function() {
				$(this).css({
					'background-color': '#25D366',
					'border-color': '#25D366'
				});
			}
		);

		// Style Request Permission button
		$('button:contains("Request Call Permission")').css({
			'background-color': '#34B7F1',
			'color': 'white',
			'border-color': '#34B7F1'
		});
	}, 100);

	// Show call permission status if available
	check_call_permission_status(frm);
}

function initiate_whatsapp_call(frm) {
	// Check if widget exists
	if (!window.whatsapp_call_widget) {
		frappe.msgprint({
			title: __('Error'),
			message: __('WhatsApp calling not initialized. Please refresh the page.'),
			indicator: 'red'
		});
		return;
	}

	// Confirm before making call
	frappe.confirm(
		__('Make WhatsApp call to {0} ({1})?', [frm.doc.lead_name, frm.doc.mobile_no]),
		function() {
			window.whatsapp_call_widget.initiate_call_from_lead(
				frm.doc.name,
				frm.doc.mobile_no,
				frm.doc.lead_name
			);
		}
	);
}

function request_call_permission(frm) {
	frappe.confirm(
		__('Send WhatsApp message requesting call permission from {0}?', [frm.doc.lead_name]),
		function() {
			frappe.call({
				method: 'whatsapp_calling.whatsapp_calling.api.permissions.request_call_permission',
				args: {
					lead_name: frm.doc.name,
					mobile_number: frm.doc.mobile_no
				},
				freeze: true,
				freeze_message: __('Sending permission request...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('Permission request sent successfully'),
							indicator: 'green'
						}, 5);

						// Refresh permission status
						check_call_permission_status(frm);
					}
				}
			});
		}
	);
}

function view_call_history(frm) {
	frappe.set_route('List', 'WhatsApp Call', {
		'lead': frm.doc.name
	});
}

function check_call_permission_status(frm) {
	// Get company's WhatsApp number
	frappe.call({
		method: 'whatsapp_calling.whatsapp_calling.api.call_control.get_company_whatsapp_number',
		args: {
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.message) {
				const wa_number = r.message.name;

				// Check permission status
				frappe.call({
					method: 'frappe.client.get_value',
					args: {
						doctype: 'Call Permission',
						filters: {
							customer_number: frm.doc.mobile_no,
							business_number: wa_number
						},
						fieldname: ['permission_status', 'expires_at', 'calls_in_24h']
					},
					callback: function(r) {
						if (r.message) {
							display_permission_status(frm, r.message);
						}
					}
				});
			}
		}
	});
}

function display_permission_status(frm, permission_data) {
	// Remove existing status if any
	$('.whatsapp-permission-status').remove();

	let status_html = '';
	const status = permission_data.permission_status;

	if (status === 'Granted') {
		const expires_at = new Date(permission_data.expires_at);
		const now = new Date();
		const days_left = Math.ceil((expires_at - now) / (1000 * 60 * 60 * 24));
		const calls_left = 5 - (permission_data.calls_in_24h || 0);

		status_html = `
			<div class="whatsapp-permission-status" style="margin: 10px 0; padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745; border-radius: 4px;">
				<strong>📞 Call Permission: Granted</strong><br>
				<small>
					Expires in ${days_left} days | ${calls_left} calls remaining today
				</small>
			</div>
		`;
	} else if (status === 'Requested') {
		status_html = `
			<div class="whatsapp-permission-status" style="margin: 10px 0; padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
				<strong>⏳ Call Permission: Requested</strong><br>
				<small>Waiting for customer approval</small>
			</div>
		`;
	} else if (status === 'Denied') {
		status_html = `
			<div class="whatsapp-permission-status" style="margin: 10px 0; padding: 10px; background-color: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px;">
				<strong>❌ Call Permission: Denied</strong><br>
				<small>Customer declined call permission</small>
			</div>
		`;
	} else if (status === 'Expired') {
		status_html = `
			<div class="whatsapp-permission-status" style="margin: 10px 0; padding: 10px; background-color: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px;">
				<strong>⏰ Call Permission: Expired</strong><br>
				<small>Please request permission again</small>
			</div>
		`;
	}

	if (status_html) {
		// Insert after mobile_no field
		frm.fields_dict.mobile_no.$wrapper.after(status_html);
	}
}
