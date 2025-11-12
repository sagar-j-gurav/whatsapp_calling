// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Call Permission', {
	refresh: function(frm) {
		// Set color indicator based on status
		if (frm.doc.permission_status === 'Granted') {
			frm.dashboard.set_headline_alert('Permission Granted', 'green');
		} else if (frm.doc.permission_status === 'Denied') {
			frm.dashboard.set_headline_alert('Permission Denied', 'red');
		} else if (frm.doc.permission_status === 'Expired') {
			frm.dashboard.set_headline_alert('Permission Expired', 'orange');
		} else {
			frm.dashboard.set_headline_alert('Permission Requested', 'blue');
		}

		// Show expiration warning
		if (frm.doc.permission_status === 'Granted' && frm.doc.expires_at) {
			const expires = new Date(frm.doc.expires_at);
			const now = new Date();
			const days_left = Math.ceil((expires - now) / (1000 * 60 * 60 * 24));

			if (days_left <= 2 && days_left > 0) {
				frappe.msgprint({
					title: __('Expiring Soon'),
					message: __('Permission expires in {0} days', [days_left]),
					indicator: 'orange'
				});
			}
		}

		// Add button to view related calls
		if (!frm.is_new()) {
			frm.add_custom_button(__('View Calls'), function() {
				frappe.set_route('List', 'WhatsApp Call', {
					'customer_number': frm.doc.customer_number,
					'business_number': frm.doc.business_number
				});
			});
		}

		// Add button to view linked lead
		if (frm.doc.lead && !frm.is_new()) {
			frm.add_custom_button(__('View Lead'), function() {
				frappe.set_route('Form', 'Lead', frm.doc.lead);
			});
		}
	}
});
