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

		// Test Webhook button
		if (frm.doc.webhook_verify_token) {
			frm.add_custom_button(__('Test Webhook'), function() {
				test_webhook(frm);
			}, __('Tests'));
		}
	}
});

function test_webhook(frm) {
	// Call server to get webhook URL and unmasked verify token
	frappe.call({
		method: 'get_webhook_test_url',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				const webhook_url = r.message.webhook_url;
				const verify_token = r.message.verify_token;
				const test_challenge = 'TEST_CHALLENGE_' + Math.floor(Math.random() * 1000000);
				const test_url = `${webhook_url}?hub.mode=subscribe&hub.verify_token=${encodeURIComponent(verify_token)}&hub.challenge=${test_challenge}`;

				// Show dialog with webhook URL and test option
				const d = new frappe.ui.Dialog({
					title: __('Webhook Configuration'),
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'webhook_info',
							options: `
								<div style="padding: 15px;">
									<h4 style="margin-top: 0;">Webhook URL</h4>
									<div style="background: #f5f5f5; padding: 12px; border-radius: 4px; margin-bottom: 20px; word-break: break-all;">
										<code style="font-size: 13px;">${webhook_url}</code>
									</div>

									<h4>Verify Token</h4>
									<div style="background: #f5f5f5; padding: 12px; border-radius: 4px; margin-bottom: 20px;">
										<code style="font-size: 13px;">${verify_token}</code>
									</div>

									<h4>Setup Instructions</h4>
									<ol style="line-height: 1.8;">
										<li>Copy the Webhook URL above</li>
										<li>Copy the Verify Token above</li>
										<li>Go to Meta App Settings → WhatsApp → Configuration</li>
										<li>Paste both values and click "Verify and Save"</li>
									</ol>

									<div style="background: #e3f2fd; padding: 12px; border-left: 4px solid #2196f3; margin-top: 20px;">
										<strong>💡 Tip:</strong> Click "Test Now" below to verify your webhook is working before configuring in Meta.
									</div>
								</div>
							`
						}
					],
					primary_action_label: __('Test Now'),
					primary_action: function() {
						// Make a test request to the webhook
						fetch(test_url)
							.then(response => {
								// Check HTTP status first
								if (!response.ok && response.status === 403) {
									return response.text().then(text => {
										frappe.msgprint({
											title: __('❌ Webhook Verification Failed'),
											message: __('Token validation failed (403 Forbidden).<br>Response: {0}<br><br>This means the webhook is working but the token does not match.', [text]),
											indicator: 'red'
										});
										throw new Error('Token validation failed');
									});
								}
								return response.text();
							})
							.then(data => {
								if (data === test_challenge) {
									frappe.msgprint({
										title: __('✅ Webhook Test Successful'),
										message: __('Your webhook is working correctly! Token validated successfully. You can now configure it in Meta.'),
										indicator: 'green'
									});
									d.hide();
								} else {
									frappe.msgprint({
										title: __('⚠️ Unexpected Response'),
										message: __('Received: {0}<br>Expected: {1}<br><br>The webhook is responding but returned unexpected data.', [data.substring(0, 200), test_challenge]),
										indicator: 'orange'
									});
								}
							})
							.catch(error => {
								if (error.message !== 'Token validation failed') {
									frappe.msgprint({
										title: __('❌ Webhook Test Failed'),
										message: __('Error: {0}<br><br>Make sure your site is accessible and the webhook endpoint is working.', [error.message]),
										indicator: 'red'
									});
								}
							});
					},
					secondary_action_label: __('Close')
				});

				d.show();
			}
		}
	});
}
