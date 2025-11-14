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

		// Test Webhook button - only show if verify token is set
		if (frm.doc.webhook_verify_token) {
			frm.add_custom_button(__('Test Webhook Verification'), function() {
				test_webhook_verification(frm);
			}, __('Tests'));
		}
	}
});

function test_webhook_verification(frm) {
	// Generate webhook URL if not already set
	let webhook_url = frm.doc.webhook_url;
	if (!webhook_url) {
		// Generate it dynamically (same as Python on_load)
		webhook_url = window.location.origin + '/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook';
	}

	const verify_token = frm.doc.webhook_verify_token;
	const test_challenge = 'TEST_CHALLENGE_' + Math.floor(Math.random() * 1000000);
	const test_url = `${webhook_url}?hub.mode=subscribe&hub.verify_token=${verify_token}&hub.challenge=${test_challenge}`;

	// Show dialog with instructions
	const d = new frappe.ui.Dialog({
		title: __('Test Webhook Verification'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'instructions',
				options: `
					<div style="padding: 15px;">
						<h4>Webhook URL</h4>
						<p><code style="background: #f5f5f5; padding: 8px; display: block; word-break: break-all;">${webhook_url}</code></p>

						<h4 style="margin-top: 20px;">Verify Token</h4>
						<p><code style="background: #f5f5f5; padding: 8px; display: block;">${verify_token || 'Not set'}</code></p>

						<h4 style="margin-top: 20px;">Test Instructions</h4>
						<ol>
							<li>Copy the webhook URL above</li>
							<li>Copy the verify token above</li>
							<li>Go to your Meta App Settings → WhatsApp → Configuration</li>
							<li>Paste the webhook URL in "Callback URL"</li>
							<li>Paste the verify token in "Verify Token"</li>
							<li>Click "Verify and Save"</li>
						</ol>

						<div style="background: #e8f5e9; padding: 12px; border-left: 4px solid #4caf50; margin-top: 20px;">
							<strong>✓ Or test locally:</strong>
							<p style="margin: 8px 0 0 0;">Click the button below to simulate Meta's verification request.</p>
						</div>
					</div>
				`
			}
		],
		primary_action_label: __('Test Locally'),
		primary_action: function() {
			// Make a test request to the webhook
			fetch(test_url)
				.then(response => response.text())
				.then(data => {
					if (data === test_challenge) {
						frappe.msgprint({
							title: __('✅ Webhook Test Successful'),
							message: __('The webhook is working correctly! You can now use this URL in Meta.<br><br><strong>Next step:</strong> Copy the URL and verify token to Meta App Settings.'),
							indicator: 'green'
						});
					} else {
						frappe.msgprint({
							title: __('⚠️ Unexpected Response'),
							message: __('Received: {0}<br>Expected: {1}<br><br>The webhook is responding but may have an issue.', [data, test_challenge]),
							indicator: 'orange'
						});
					}
					d.hide();
				})
				.catch(error => {
					frappe.msgprint({
						title: __('❌ Webhook Test Failed'),
						message: __('Error: {0}<br><br>Make sure:<br>1. Your site is running<br>2. The webhook endpoint is accessible', [error.message]),
						indicator: 'red'
					});
				});
		}
	});

	d.show();
}
