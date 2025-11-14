// WhatsApp Calling integration for CRM Lead
frappe.ui.form.on('CRM Lead', {
	refresh: function(frm) {
		// Only show button if lead has mobile number
		if (frm.doc.mobile_no) {
			frm.add_custom_button(__('WhatsApp Call'), function() {
				initiate_whatsapp_call(frm);
			}, __('Actions'));
		}
	}
});

function initiate_whatsapp_call(frm) {
	// Show dialog to confirm call initiation
	frappe.confirm(
		__('Initiate WhatsApp call to {0}?', [frm.doc.mobile_no]),
		function() {
			// Call the server method to initiate the call
			frappe.call({
				method: 'whatsapp_calling.whatsapp_calling.api.call_control.initiate_call',
				args: {
					to_number: frm.doc.mobile_no,
					lead: frm.doc.name,
					lead_name: frm.doc.lead_name || frm.doc.first_name
				},
				freeze: true,
				freeze_message: __('Initiating WhatsApp call...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('Call initiated successfully! Call ID: {0}', [r.message.call_id]),
							indicator: 'green'
						}, 5);

						// Refresh to show any updates
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __('Call Failed'),
							message: r.message.error || __('Could not initiate call. Please check error log.'),
							indicator: 'red'
						});
					}
				},
				error: function(r) {
					frappe.msgprint({
						title: __('Error'),
						message: __('Failed to initiate call. Please check your configuration.'),
						indicator: 'red'
					});
				}
			});
		}
	);
}
