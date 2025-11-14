// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Settings', {
	refresh: function(frm) {
		// Test Janus Connection button
		if (frm.doc.janus_http_url) {
			frm.add_custom_button(__('Test Janus Connection'), function() {
				frappe.call({
					method: 'test_janus_connection',
					doc: frm.doc,
					callback: function(r) {
						if (!r.exc) {
							frappe.msgprint(__('Janus connection test completed. Check messages above.'));
						}
					}
				});
			}, __('Tests'));
		}
	}
});
