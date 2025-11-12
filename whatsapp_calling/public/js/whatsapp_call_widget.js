// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.provide('whatsapp_calling');

whatsapp_calling.CallWidget = class {
	constructor() {
		this.peer_connection = null;
		this.local_stream = null;
		this.call_id = null;
		this.call_name = null;
		this.call_status = 'idle';
		this.timer_interval = null;

		this.setup_realtime_listeners();
	}

	setup_realtime_listeners() {
		// Listen for incoming calls
		frappe.realtime.on('incoming_whatsapp_call', (data) => {
			this.show_incoming_call_dialog(data);
		});

		// Listen for call status updates
		frappe.realtime.on('call_status_update', (data) => {
			this.handle_status_update(data);
		});
	}

	async initiate_call_from_lead(lead_name, mobile_number, lead_display_name) {
		try {
			// Show calling dialog
			this.show_calling_dialog(lead_display_name, mobile_number);

			// Request microphone
			this.local_stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: true,
					noiseSuppression: true,
					autoGainControl: true
				}
			});

			// Call backend to initiate call
			const response = await frappe.call({
				method: 'whatsapp_calling.whatsapp_calling.api.call_control.make_call',
				args: {
					lead_name: lead_name,
					mobile_number: mobile_number
				}
			});

			if (response.message && response.message.success) {
				this.call_id = response.message.call_id;
				this.call_name = response.message.call_name;

				// Setup WebRTC
				await this.setup_webrtc(response.message.webrtc_config);

				// Update dialog to show "Calling..."
				this.update_calling_dialog_status('Calling...');

				// Start polling for answer
				this.poll_for_answer();
			}
		} catch (error) {
			console.error('Call initiation error:', error);
			frappe.msgprint(__('Failed to initiate call: {0}', [error.message]));
			this.cleanup();
		}
	}

	async setup_webrtc(config) {
		try {
			// Create peer connection
			this.peer_connection = new RTCPeerConnection({
				iceServers: [
					{ urls: 'stun:stun.l.google.com:19302' },
					{ urls: 'stun:stun1.l.google.com:19302' }
				]
			});

			// Add local audio track
			this.local_stream.getTracks().forEach(track => {
				this.peer_connection.addTrack(track, this.local_stream);
			});

			// Handle remote stream
			this.peer_connection.ontrack = (event) => {
				this.play_remote_audio(event.streams[0]);
			};

			// Handle ICE candidates
			this.peer_connection.onicecandidate = (event) => {
				if (event.candidate) {
					console.log('ICE candidate:', event.candidate);
					// Send to Janus via signaling server (implement if needed)
				}
			};

			// Handle connection state changes
			this.peer_connection.onconnectionstatechange = (event) => {
				console.log('Connection state:', this.peer_connection.connectionState);
				if (this.peer_connection.connectionState === 'connected') {
					this.show_active_call_ui();
				}
			};

			// Create offer
			const offer = await this.peer_connection.createOffer();
			await this.peer_connection.setLocalDescription(offer);

			// TODO: Send offer to Janus and get answer
			// For now, Janus will handle this via WhatsApp API connection

			console.log('WebRTC setup complete');
		} catch (error) {
			console.error('WebRTC setup error:', error);
			throw error;
		}
	}

	play_remote_audio(stream) {
		// Remove existing audio element
		$('#whatsapp_remote_audio').remove();

		// Create new audio element
		const audio = document.createElement('audio');
		audio.id = 'whatsapp_remote_audio';
		audio.srcObject = stream;
		audio.autoplay = true;
		document.body.appendChild(audio);

		console.log('Remote audio playing');
	}

	show_calling_dialog(name, number) {
		this.calling_dialog = new frappe.ui.Dialog({
			title: __('Calling...'),
			fields: [{
				fieldtype: 'HTML',
				fieldname: 'calling_html',
				options: `
					<div style="text-align: center; padding: 30px;">
						<div style="font-size: 48px; margin-bottom: 20px;">📞</div>
						<h3>${name}</h3>
						<p style="color: #666;">${number}</p>
						<p id="calling_status" style="color: #25D366; margin-top: 20px;">
							<span class="indicator blue">Initiating call...</span>
						</p>
					</div>
				`
			}],
			primary_action_label: __('Cancel'),
			primary_action: () => {
				this.end_call();
			}
		});

		this.calling_dialog.show();
	}

	update_calling_dialog_status(status) {
		$('#calling_status').html(`<span class="indicator orange">${status}</span>`);
	}

	show_incoming_call_dialog(call_data) {
		// Play ringtone
		this.play_ringtone();

		const dialog = new frappe.ui.Dialog({
			title: __('Incoming WhatsApp Call'),
			fields: [{
				fieldtype: 'HTML',
				fieldname: 'incoming_html',
				options: `
					<div style="text-align: center; padding: 30px;" class="incoming-call">
						<div style="font-size: 64px; margin-bottom: 20px;">📱</div>
						<h2>${call_data.customer_name}</h2>
						<p style="color: #666; font-size: 16px;">${call_data.customer_number}</p>
					</div>
				`
			}],
			primary_action_label: __('Answer'),
			primary_action: () => {
				this.stop_ringtone();
				this.answer_incoming_call(call_data.call_id);
				dialog.hide();
			},
			secondary_action_label: __('Decline'),
			secondary_action: () => {
				this.stop_ringtone();
				dialog.hide();
			}
		});

		dialog.show();
	}

	async answer_incoming_call(call_id) {
		try {
			// Request microphone
			this.local_stream = await navigator.mediaDevices.getUserMedia({ audio: true });

			// Call backend
			const response = await frappe.call({
				method: 'whatsapp_calling.whatsapp_calling.api.call_control.answer_call',
				args: { call_id: call_id }
			});

			if (response.message && response.message.success) {
				this.call_id = call_id;

				// Setup WebRTC
				await this.setup_webrtc(response.message.webrtc_config);

				// Show active call UI
				this.show_active_call_ui();
			}
		} catch (error) {
			frappe.msgprint(__('Failed to answer call: {0}', [error.message]));
		}
	}

	show_active_call_ui() {
		this.call_status = 'active';

		// Remove calling dialog if exists
		if (this.calling_dialog) {
			this.calling_dialog.hide();
		}

		// Create floating call panel
		const panel_html = `
			<div id="whatsapp_call_panel" class="whatsapp-call-panel">
				<div class="whatsapp-call-header">
					<div>
						<strong>WhatsApp Call Active</strong>
					</div>
					<div class="call-timer" id="call_timer">00:00</div>
					<div class="call-controls">
						<button class="btn btn-sm" id="mute_btn" style="margin-right: 8px;">
							<svg class="icon icon-sm"><use href="#icon-mic"></use></svg> Mute
						</button>
						<button class="btn btn-sm btn-danger" id="end_call_btn">
							<svg class="icon icon-sm"><use href="#icon-phone"></use></svg> End Call
						</button>
					</div>
				</div>
			</div>
		`;

		$('body').append(panel_html);

		// Bind events
		$('#end_call_btn').on('click', () => this.end_call());
		$('#mute_btn').on('click', () => this.toggle_mute());

		// Start timer
		this.start_call_timer();
	}

	start_call_timer() {
		let seconds = 0;
		this.timer_interval = setInterval(() => {
			seconds++;
			const mins = Math.floor(seconds / 60);
			const secs = seconds % 60;
			$('#call_timer').text(
				`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
			);
		}, 1000);
	}

	toggle_mute() {
		if (this.local_stream) {
			const audioTrack = this.local_stream.getAudioTracks()[0];
			if (audioTrack) {
				audioTrack.enabled = !audioTrack.enabled;
				$('#mute_btn').html(
					audioTrack.enabled
						? '<svg class="icon icon-sm"><use href="#icon-mic"></use></svg> Mute'
						: '<svg class="icon icon-sm"><use href="#icon-mic-off"></use></svg> Unmute'
				);
			}
		}
	}

	async end_call() {
		try {
			if (this.call_id) {
				await frappe.call({
					method: 'whatsapp_calling.whatsapp_calling.api.call_control.end_call',
					args: { call_id: this.call_id }
				});
			}
		} finally {
			this.cleanup();
		}
	}

	cleanup() {
		// Stop timer
		if (this.timer_interval) {
			clearInterval(this.timer_interval);
		}

		// Stop media
		if (this.local_stream) {
			this.local_stream.getTracks().forEach(track => track.stop());
		}

		// Close peer connection
		if (this.peer_connection) {
			this.peer_connection.close();
		}

		// Remove UI
		$('#whatsapp_call_panel').remove();
		$('#whatsapp_remote_audio').remove();

		if (this.calling_dialog) {
			this.calling_dialog.hide();
		}

		// Reset state
		this.call_status = 'idle';
		this.call_id = null;
		this.peer_connection = null;
		this.local_stream = null;
	}

	poll_for_answer() {
		// Poll every 2 seconds for 60 seconds
		let attempts = 0;
		const poll_interval = setInterval(() => {
			attempts++;

			// Check if call was answered (via webhook update)
			if (this.call_status === 'active') {
				clearInterval(poll_interval);
				return;
			}

			if (attempts >= 30) {
				clearInterval(poll_interval);
				frappe.msgprint(__('Call not answered'));
				this.cleanup();
			}
		}, 2000);
	}

	handle_status_update(data) {
		if (data.call_id === this.call_id) {
			if (data.status === 'Answered') {
				this.call_status = 'active';
				this.show_active_call_ui();
			} else if (data.status === 'Ended') {
				this.cleanup();
				frappe.msgprint(__('Call ended'));
			}
		}
	}

	play_ringtone() {
		// Create audio element for ringtone
		const audio = document.createElement('audio');
		audio.id = 'whatsapp_ringtone';
		audio.loop = true;
		audio.src = '/assets/whatsapp_calling/sounds/ringtone.mp3';
		document.body.appendChild(audio);
		audio.play().catch(e => console.log('Ringtone play failed:', e));
	}

	stop_ringtone() {
		const ringtone = document.getElementById('whatsapp_ringtone');
		if (ringtone) {
			ringtone.pause();
			ringtone.remove();
		}
	}
};

// Initialize on page load
frappe.ready(() => {
	if (frappe.session.user !== 'Guest') {
		window.whatsapp_call_widget = new whatsapp_calling.CallWidget();
	}
});
