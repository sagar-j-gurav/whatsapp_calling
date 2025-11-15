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
		console.log('frappe.realtime object:', frappe.realtime);
		console.log('Current user:', frappe.session.user);

		// Listen for incoming calls
		frappe.realtime.on('incoming_whatsapp_call', (data) => {
			console.log('╔═══════════════════════════════════════════════════════╗');
			console.log('║  INCOMING WHATSAPP CALL EVENT RECEIVED               ║');
			console.log('╚═══════════════════════════════════════════════════════╝');
			console.log('Call data:', JSON.stringify(data, null, 2));
			console.log('Widget instance:', this);
			console.log('About to call show_incoming_call_dialog...');

			try {
				this.show_incoming_call_dialog(data);
				console.log('✓ show_incoming_call_dialog called successfully');
			} catch (error) {
				console.error('ERROR calling show_incoming_call_dialog:', error);
				console.error('Error stack:', error.stack);
			}
		});

		// Listen for call status updates
		frappe.realtime.on('call_status_update', (data) => {
			console.log('=== CALL STATUS UPDATE EVENT RECEIVED ===');
			console.log('Status data:', data);
			this.handle_status_update(data);
		});

		console.log('✓ Realtime listeners registered successfully');
		console.log('Widget is ready to receive incoming call events');
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
			console.log('=== Setting up WebRTC connection to Janus ===');
			console.log('Config:', config);

			// Get Janus HTTP URL from settings
			const janus_http_url = await this.get_janus_http_url();
			const room_id = config.room_id;

			console.log(`Janus HTTP URL: ${janus_http_url}`);
			console.log(`Room ID to join: ${room_id}`);

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
				console.log('Added local audio track');
			});

			// Handle remote stream
			this.peer_connection.ontrack = (event) => {
				console.log('Received remote track!');
				this.play_remote_audio(event.streams[0]);
			};

			// Handle ICE candidates - send them to Janus via trickle
			this.peer_connection.onicecandidate = (event) => {
				if (event.candidate) {
					console.log('ICE candidate generated:', event.candidate);
					// Janus will handle ICE through the initial offer/answer
				}
			};

			// Handle connection state changes
			this.peer_connection.onconnectionstatechange = (event) => {
				console.log('Peer connection state:', this.peer_connection.connectionState);
				if (this.peer_connection.connectionState === 'connected') {
					console.log('✓ WebRTC connection established!');
				} else if (this.peer_connection.connectionState === 'failed') {
					console.error('✗ WebRTC connection failed');
					frappe.show_alert({message: 'Connection failed', indicator: 'red'});
				}
			};

			// Create SDP offer
			console.log('Creating SDP offer...');
			const offer = await this.peer_connection.createOffer({
				offerToReceiveAudio: true
			});
			await this.peer_connection.setLocalDescription(offer);
			console.log('✓ Local SDP set');

			// Now join the Janus AudioBridge room
			console.log(`Joining Janus room ${room_id}...`);
			const answer = await this.join_janus_room(janus_http_url, room_id, offer.sdp);

			// Set remote description
			console.log('Setting remote SDP answer...');
			await this.peer_connection.setRemoteDescription({
				type: 'answer',
				sdp: answer
			});
			console.log('✓ Remote SDP set - WebRTC connection established!');

		} catch (error) {
			console.error('WebRTC setup error:', error);
			throw error;
		}
	}

	async get_janus_http_url() {
		// Get Janus HTTP URL from WhatsApp Settings
		const response = await frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'WhatsApp Settings',
				filters: {},
				fieldname: 'janus_http_url'
			}
		});
		return response.message.janus_http_url;
	}

	async join_janus_room(janus_http_url, room_id, sdp_offer) {
		console.log('=== Joining Janus AudioBridge Room ===');

		// Step 1: Create Janus session
		console.log('Creating Janus session...');
		const session_response = await fetch(janus_http_url, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({
				janus: 'create',
				transaction: this.generate_transaction_id()
			})
		});
		const session_data = await session_response.json();
		const session_id = session_data.data.id;
		console.log(`✓ Session created: ${session_id}`);

		// Step 2: Attach AudioBridge plugin
		console.log('Attaching AudioBridge plugin...');
		const attach_response = await fetch(`${janus_http_url}/${session_id}`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({
				janus: 'attach',
				plugin: 'janus.plugin.audiobridge',
				transaction: this.generate_transaction_id()
			})
		});
		const attach_data = await attach_response.json();
		const handle_id = attach_data.data.id;
		console.log(`✓ Plugin attached: ${handle_id}`);

		// Store for cleanup
		this.janus_session_id = session_id;
		this.janus_handle_id = handle_id;

		// Step 3: Join the room with our SDP offer
		console.log(`Joining room ${room_id} with SDP offer...`);
		const join_response = await fetch(`${janus_http_url}/${session_id}/${handle_id}`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({
				janus: 'message',
				transaction: this.generate_transaction_id(),
				body: {
					request: 'join',
					room: parseInt(room_id),
					display: frappe.session.user
				},
				jsep: {
					type: 'offer',
					sdp: sdp_offer
				}
			})
		});

		const join_data = await join_response.json();
		console.log('Join response:', join_data);

		// Check for immediate answer
		if (join_data.jsep && join_data.jsep.type === 'answer') {
			console.log('✓ Received SDP answer immediately');
			return join_data.jsep.sdp;
		}

		// Poll for SDP answer in events
		if (join_data.janus === 'ack') {
			console.log('Received ack, polling for SDP answer...');
			for (let i = 0; i < 50; i++) {
				await new Promise(resolve => setTimeout(resolve, 100));

				const event_response = await fetch(`${janus_http_url}/${session_id}?maxev=1`);
				const event_data = await event_response.json();

				if (event_data.jsep && event_data.jsep.type === 'answer') {
					console.log(`✓ Received SDP answer after ${i + 1} polls`);
					return event_data.jsep.sdp;
				}
			}
			throw new Error('Timeout waiting for SDP answer from Janus');
		}

		throw new Error('Unexpected response from Janus');
	}

	generate_transaction_id() {
		return Math.random().toString(36).substring(2, 15);
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
		console.log('╔═══════════════════════════════════════════════════════╗');
		console.log('║  SHOW_INCOMING_CALL_DIALOG - START                   ║');
		console.log('╚═══════════════════════════════════════════════════════╝');
		console.log('Call data:', call_data);
		console.log('Step 1: Check for existing overlay...');

		// Remove any existing overlay first
		const existingOverlay = $('#wa-call-overlay');
		if (existingOverlay.length > 0) {
			console.log('Found existing overlay, removing it first...');
			existingOverlay.remove();
		} else {
			console.log('No existing overlay found');
		}

		console.log('Step 2: Playing ringtone...');
		// Play ringtone
		this.play_ringtone();
		console.log('✓ Ringtone playing');

		console.log('Step 3: Storing call data...');
		// Store call data
		this.current_call_data = call_data;
		console.log('✓ Call data stored');

		// Format display name: Lead Name (WhatsApp Profile) or just WhatsApp Profile
		let displayName = 'Unknown';
		if (call_data.lead_name && call_data.wa_profile_name) {
			// Both available: "Lead Name (WhatsApp Profile)"
			displayName = `${call_data.lead_name} <span style="opacity: 0.7; font-size: 0.85em;">(${call_data.wa_profile_name})</span>`;
		} else if (call_data.lead_name) {
			// Only lead name
			displayName = call_data.lead_name;
		} else if (call_data.wa_profile_name) {
			// Only WhatsApp profile name
			displayName = call_data.wa_profile_name;
		} else if (call_data.customer_name && call_data.customer_name !== 'Unknown') {
			// Fallback to customer_name
			displayName = call_data.customer_name;
		}

		console.log('Step 4: Formatting display name...');
		console.log('Display name will be:', displayName);

		console.log('Step 5: Creating overlay HTML...');
		// Create WhatsApp-style overlay
		const overlay = $(`
			<div class="whatsapp-call-overlay" id="wa-call-overlay">
				<div class="whatsapp-call-card" id="wa-call-card">
					<!-- Header -->
					<div class="wa-call-header" id="wa-call-drag-handle">
						<div class="wa-call-status">WhatsApp Voice Call</div>
						<button class="wa-call-expand-btn" id="wa-expand-btn" title="Maximize">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<polyline points="15 3 21 3 21 9"></polyline>
								<polyline points="9 21 3 21 3 15"></polyline>
								<line x1="21" y1="3" x2="14" y2="10"></line>
								<line x1="3" y1="21" x2="10" y2="14"></line>
							</svg>
						</button>
					</div>

					<!-- Caller Info -->
					<div class="wa-call-content">
						<div class="wa-caller-avatar">
							<svg width="80" height="80" viewBox="0 0 80 80">
								<circle cx="40" cy="40" r="40" fill="#25D366"/>
								<path d="M40 20c-11.046 0-20 8.954-20 20s8.954 20 20 20 20-8.954 20-20-8.954-20-20-20zm0 6c3.314 0 6 2.686 6 6s-2.686 6-6 6-6-2.686-6-6 2.686-6 6-6zm0 28c-5 0-9.42-2.558-12-6.438 0.06-3.98 8-6.162 12-6.162s11.94 2.182 12 6.162c-2.58 3.88-7 6.438-12 6.438z" fill="white"/>
							</svg>
						</div>

						<div class="wa-caller-name">${displayName}</div>
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
		console.log('✓ Overlay HTML created. jQuery object:', overlay);
		console.log('Overlay length:', overlay.length);

		console.log('Step 6: Appending overlay to body...');
		// Append to body
		$('body').append(overlay);
		console.log('✓ Overlay appended to body');

		// Verify it's in the DOM
		const checkOverlay = $('#wa-call-overlay');
		console.log('Verification - Overlay in DOM:', checkOverlay.length > 0);
		console.log('Overlay element:', checkOverlay[0]);
		if (checkOverlay.length > 0) {
			console.log('Overlay computed style:', window.getComputedStyle(checkOverlay[0]));
		}

		console.log('Step 7: Triggering show animation...');
		// Trigger animation
		setTimeout(() => {
			overlay.addClass('show');
			console.log('✓ Added "show" class to overlay');
			console.log('Overlay classes:', overlay.attr('class'));
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

		// Maximize/Minimize toggle
		$('#wa-expand-btn').on('click', (e) => {
			e.stopPropagation();
			const card = $('#wa-call-card');
			card.toggleClass('maximized');

			// Update button icon
			const btn = $('#wa-expand-btn');
			if (card.hasClass('maximized')) {
				btn.attr('title', 'Minimize');
				btn.html(`
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="4 14 10 14 10 20"></polyline>
						<polyline points="20 10 14 10 14 4"></polyline>
						<line x1="14" y1="10" x2="21" y2="3"></line>
						<line x1="3" y1="21" x2="10" y2="14"></line>
					</svg>
				`);
			} else {
				btn.attr('title', 'Maximize');
				btn.html(`
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="15 3 21 3 21 9"></polyline>
						<polyline points="9 21 3 21 3 15"></polyline>
						<line x1="21" y1="3" x2="14" y2="10"></line>
						<line x1="3" y1="21" x2="10" y2="14"></line>
					</svg>
				`);
			}
		});

		console.log('Step 8: Setting up drag functionality...');
		// Make draggable
		this.make_draggable($('#wa-call-card'), $('#wa-call-drag-handle'));
		console.log('✓ Drag functionality set up');

		console.log('╔═══════════════════════════════════════════════════════╗');
		console.log('║  SHOW_INCOMING_CALL_DIALOG - COMPLETE                ║');
		console.log('╚═══════════════════════════════════════════════════════╝');
	}

	// Test function - can be called from console for debugging
	test_show_popup() {
		console.log('Testing popup with fake call data...');
		this.show_incoming_call_dialog({
			call_id: 'test_call_123',
			call_name: 'WC-2024-00001',
			customer_number: '+919876543210',
			customer_name: 'Test Customer',
			lead: null,
			lead_name: 'Test Lead',
			wa_profile_name: 'WhatsApp User'
		});
	}

	make_draggable(element, handle) {
		let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

		handle.on('mousedown', (e) => {
			// Don't drag if maximized or clicking expand button
			if (element.hasClass('maximized') || $(e.target).closest('#wa-expand-btn').length) {
				return;
			}

			e.preventDefault();
			pos3 = e.clientX;
			pos4 = e.clientY;

			$(document).on('mouseup.drag', () => {
				$(document).off('mouseup.drag mousemove.drag');
			});

			$(document).on('mousemove.drag', (e) => {
				e.preventDefault();
				pos1 = pos3 - e.clientX;
				pos2 = pos4 - e.clientY;
				pos3 = e.clientX;
				pos4 = e.clientY;

				const parent = element.parent();
				let newTop = parent.offset().top - pos2;
				let newRight = $(window).width() - parent.offset().left - parent.width() + pos1;

				// Keep within viewport
				newTop = Math.max(0, Math.min(newTop, $(window).height() - element.height()));
				newRight = Math.max(0, Math.min(newRight, $(window).width() - element.width()));

				parent.css({
					top: newTop + 'px',
					right: newRight + 'px'
				});
			});
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
		console.log('Call status update received:', data);

		// Handle incoming call status updates
		if (data.status === 'Ended') {
			// Hide the call overlay if it's showing
			this.hide_call_overlay();

			// Cleanup resources
			this.cleanup();

			// Show notification
			if (data.duration) {
				frappe.show_alert({
					message: __('Call ended. Duration: {0} seconds', [data.duration]),
					indicator: 'blue'
				});
			} else {
				frappe.show_alert({
					message: __('Call ended'),
					indicator: 'blue'
				});
			}
		} else if (data.call_id === this.call_id) {
			if (data.status === 'Answered') {
				this.call_status = 'active';
				this.show_active_call_ui();
			}
		}
	}

	play_ringtone() {
		try {
			// Use browser's built-in beep or oscillator as ringtone
			const audioContext = new (window.AudioContext || window.webkitAudioContext)();

			// Create beeping pattern - create new oscillator each time
			this.ringtone_interval = setInterval(() => {
				try {
					const oscillator = audioContext.createOscillator();
					const gainNode = audioContext.createGain();

					oscillator.connect(gainNode);
					gainNode.connect(audioContext.destination);

					oscillator.frequency.value = 800; // Hz
					oscillator.type = 'sine';
					gainNode.gain.value = 0.3;

					oscillator.start(0);
					oscillator.stop(audioContext.currentTime + 0.2); // 200ms beep
				} catch (e) {
					console.log('Beep creation failed:', e);
				}
			}, 1000); // Beep every second

			// Store context for cleanup
			this.ringtone_context = audioContext;

			console.log('Playing ringtone (oscillator)');
		} catch (e) {
			console.log('Ringtone initialization failed:', e);
			// Fallback: Use system notification sound
			try {
				const audio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==');
				audio.loop = true;
				audio.play().catch(err => console.log('Fallback ringtone failed:', err));
			} catch (err) {
				console.log('All ringtone methods failed');
			}
		}
	}

	stop_ringtone() {
		// Stop oscillator interval
		if (this.ringtone_interval) {
			clearInterval(this.ringtone_interval);
			this.ringtone_interval = null;
		}

		// Close audio context
		if (this.ringtone_context) {
			this.ringtone_context.close().catch(e => console.log('AudioContext close failed:', e));
			this.ringtone_context = null;
		}

		// Clean up any legacy audio element
		const ringtone = document.getElementById('whatsapp_ringtone');
		if (ringtone) {
			ringtone.pause();
			ringtone.remove();
		}

		console.log('Ringtone stopped');
	}
};

// Initialize on page load
$(document).ready(function() {
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
