// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Number', {
	refresh: function(frm) {
		// Add custom buttons
		if (!frm.is_new() && frm.doc.status === 'Active') {
			frm.add_custom_button(__('View Calls'), function() {
				frappe.set_route('List', 'WhatsApp Call', {
					'business_number': frm.doc.name
				});
			});
		}

		// Set color indicator based on status
		if (frm.doc.status === 'Active') {
			frm.dashboard.set_headline_alert('Status: Active', 'green');
		} else if (frm.doc.status === 'Inactive') {
			frm.dashboard.set_headline_alert('Status: Inactive', 'red');
		} else {
			frm.dashboard.set_headline_alert('Status: Pending Verification', 'orange');
		}
	},

	phone_number: function(frm) {
		// Auto-format phone number
		if (frm.doc.phone_number && !frm.doc.phone_number.startsWith('+')) {
			frappe.msgprint(__('Phone number should start with + (e.g., +919876543210)'));
		}
	}
});
