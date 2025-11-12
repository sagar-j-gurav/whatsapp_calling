// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Call', {
	refresh: function(frm) {
		// Set color indicator based on status
		if (frm.doc.status === 'Answered') {
			frm.dashboard.set_headline_alert('Call Answered', 'green');
		} else if (frm.doc.status === 'Ended') {
			frm.dashboard.set_headline_alert('Call Ended', 'blue');
		} else if (frm.doc.status === 'Failed' || frm.doc.status === 'No Answer') {
			frm.dashboard.set_headline_alert(`Call ${frm.doc.status}`, 'red');
		} else if (frm.doc.status === 'Ringing') {
			frm.dashboard.set_headline_alert('Call Ringing', 'orange');
		}

		// Add button to view linked lead
		if (frm.doc.lead && !frm.is_new()) {
			frm.add_custom_button(__('View Lead'), function() {
				frappe.set_route('Form', 'Lead', frm.doc.lead);
			});
		}

		// Add button to play recording
		if (frm.doc.recording_file && !frm.is_new()) {
			frm.add_custom_button(__('Play Recording'), function() {
				window.open(frm.doc.recording_file, '_blank');
			});
		}

		// Format duration display
		if (frm.doc.duration_seconds) {
			const mins = Math.floor(frm.doc.duration_seconds / 60);
			const secs = frm.doc.duration_seconds % 60;
			frm.set_df_property('duration_seconds', 'description',
				`${mins}m ${secs}s`);
		}
	},

	customer_number: function(frm) {
		// Try to find and link lead automatically
		if (frm.doc.customer_number && !frm.doc.lead) {
			frappe.call({
				method: 'whatsapp_calling.whatsapp_calling.api.call_control.find_lead_by_mobile',
				args: {
					mobile_number: frm.doc.customer_number
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('lead', r.message);
					}
				}
			});
		}
	}
});
