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
		console.log('=== WhatsApp Call Widget: Setting up realtime listeners ===');

		// Listen for incoming calls
		frappe.realtime.on('incoming_whatsapp_call', (data) => {
			console.log('=== INCOMING WHATSAPP CALL EVENT RECEIVED ===');
			console.log('Call data:', data);
			this.show_incoming_call_dialog(data);
		});

		// Listen for call status updates
		frappe.realtime.on('call_status_update', (data) => {
			console.log('=== CALL STATUS UPDATE EVENT RECEIVED ===');
			console.log('Status data:', data);
			this.handle_status_update(data);
		});

		console.log('✓ Realtime listeners registered successfully');
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
		console.log('=== SHOWING INCOMING CALL DIALOG ===');
		console.log('Call data:', call_data);

		// Play ringtone
		this.play_ringtone();

		// Store call data
		this.current_call_data = call_data;

		// Create WhatsApp-style overlay
		const overlay = $(`
			<div class="whatsapp-call-overlay" id="wa-call-overlay">
				<div class="whatsapp-call-card">
					<!-- Header -->
					<div class="wa-call-header">
						<div class="wa-call-status">WhatsApp Voice Call</div>
					</div>

					<!-- Caller Info -->
					<div class="wa-call-content">
						<div class="wa-caller-avatar">
							<svg width="80" height="80" viewBox="0 0 80 80">
								<circle cx="40" cy="40" r="40" fill="#25D366"/>
								<path d="M40 20c-11.046 0-20 8.954-20 20s8.954 20 20 20 20-8.954 20-20-8.954-20-20-20zm0 6c3.314 0 6 2.686 6 6s-2.686 6-6 6-6-2.686-6-6 2.686-6 6-6zm0 28c-5 0-9.42-2.558-12-6.438 0.06-3.98 8-6.162 12-6.162s11.94 2.182 12 6.162c-2.58 3.88-7 6.438-12 6.438z" fill="white"/>
							</svg>
						</div>

						<div class="wa-caller-name">${call_data.customer_name || 'Unknown'}</div>
						<div class="wa-caller-number">${call_data.customer_number || ''}</div>

						${call_data.lead ? `
							<a href="/app/crm-lead/${call_data.lead}" target="_blank" class="wa-lead-link">
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
									<circle cx="12" cy="7" r="4"></circle>
								</svg>
								View Lead Details
							</a>
						` : ''}

						<div class="wa-call-ringing">Incoming...</div>
					</div>

					<!-- Action Buttons -->
					<div class="wa-call-actions">
						<button class="wa-btn wa-btn-decline" id="wa-decline-btn">
							<svg width="28" height="28" viewBox="0 0 24 24" fill="white">
								<path d="M12 9c-1.6 0-3.15.25-4.6.72v3.1c0 .39-.23.74-.56.9-.98.49-1.87 1.12-2.66 1.85-.18.18-.43.28-.7.28-.28 0-.53-.11-.71-.29L.29 13.08c-.18-.17-.29-.42-.29-.7 0-.28.11-.53.29-.71C3.34 8.78 7.46 7 12 7s8.66 1.78 11.71 4.67c.18.18.29.43.29.71 0 .28-.11.53-.29.71l-2.48 2.48c-.18.18-.43.29-.71.29-.27 0-.52-.11-.7-.28-.79-.74-1.68-1.36-2.66-1.85-.33-.16-.56-.5-.56-.9v-3.1C15.15 9.25 13.6 9 12 9z"/>
							</svg>
							<span>Decline</span>
						</button>

						<button class="wa-btn wa-btn-answer" id="wa-answer-btn">
							<svg width="28" height="28" viewBox="0 0 24 24" fill="white">
								<path d="M20.01 15.38c-1.23 0-2.42-.2-3.53-.56-.35-.12-.74-.03-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z"/>
							</svg>
							<span>Answer</span>
						</button>
					</div>
				</div>
			</div>
		`);

		// Append to body
		$('body').append(overlay);

		// Trigger animation
		setTimeout(() => {
			overlay.addClass('show');
		}, 10);

		// Bind actions
		$('#wa-decline-btn').on('click', () => {
			this.stop_ringtone();
			this.decline_call(call_data.call_id);
			this.hide_call_overlay();
		});

		$('#wa-answer-btn').on('click', () => {
			this.stop_ringtone();
			this.answer_incoming_call(call_data.call_id);
			this.hide_call_overlay();
		});
	}

	hide_call_overlay() {
		const overlay = $('#wa-call-overlay');
		overlay.removeClass('show');
		setTimeout(() => {
			overlay.remove();
		}, 300);
	}

	decline_call(call_id) {
		// Call backend to decline/reject the call
		frappe.call({
			method: 'whatsapp_calling.whatsapp_calling.api.call_control.end_call',
			args: { call_id: call_id }
		});
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
	console.log('=== WhatsApp Call Widget: Initializing ===');
	console.log('Current user:', frappe.session.user);

	if (frappe.session.user !== 'Guest') {
		window.whatsapp_call_widget = new whatsapp_calling.CallWidget();
		console.log('✓ WhatsApp Call Widget initialized successfully');
		console.log('Widget instance:', window.whatsapp_call_widget);
	} else {
		console.log('⚠ Skipping widget initialization - user is Guest');
	}
});
