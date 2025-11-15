# Janus Production Setup Guide

Production-grade Janus Gateway configuration for WhatsApp Business Calling integration, following Meta's recommended best practices.

## Prerequisites

- **Operating System**: CentOS 9, Ubuntu 20.04+, or any Linux compatible with Janus
- **Public IP Address**: Required for production deployment
- **Domain Name**: Optional but recommended for SSL/TLS
- **Janus Gateway**: Version 1.3.3 or later (tested version from Meta docs)

## 1. Building and Installing Janus

Follow the official Janus installation guide:

```bash
# Refer to https://github.com/meetecho/janus-gateway
# This guide was tested using version 1.3.3
```

### Recommended Installation Path
```
/usr/share/janus/
├── bin/janus
├── etc/janus/
│   ├── janus.jcfg
│   ├── janus.plugin.audiobridge.jcfg
│   └── ...
└── lib/
```

## 2. Janus NAT Configuration (Critical for Production)

### 2.1 Configure nat_1_1_mapping in janus.jcfg

**File**: `/usr/share/janus/etc/janus/janus.jcfg`

Set `nat_1_1_mapping` to your server's public IP address:

```javascript
general: {
    # ... other settings ...

    # CRITICAL: Set this to your public IP address
    # This tells Janus to advertise this IP in ICE candidates
    nat_1_1_mapping = "YOUR_PUBLIC_IP_ADDRESS"

    # Example:
    # nat_1_1_mapping = "203.0.113.42"
}
```

**Important**: Replace `YOUR_PUBLIC_IP_ADDRESS` with your actual public IP. This is required for WebRTC NAT traversal.

### 2.2 STUN Server Configuration

Meta recommends using Google's STUN server when starting Janus:

```bash
/usr/share/janus/bin/janus \
    --debug-level=6 \
    --libnice-debug=on \
    -S stun.l.google.com:19302 \
    --log-file=/var/log/janus.log \
    --config=/usr/share/janus/etc/janus/janus.jcfg
```

**Key Parameters**:
- `--debug-level=6`: Enable debug logging (reduce in production if needed)
- `--libnice-debug=on`: Enable ICE debugging
- `-S stun.l.google.com:19302`: Use Google STUN server (Meta recommended)
- `--log-file`: Log file location
- `--config`: Path to janus.jcfg

## 3. AudioBridge Plugin Configuration

**File**: `/usr/share/janus/etc/janus/janus.plugin.audiobridge.jcfg`

```javascript
general: {
    # Admin key for creating/destroying rooms programmatically
    admin_key = "your_admin_secret_here"

    # Enable recording if needed
    record_tmp_ext = "opus"
}
```

**Note**: Rooms are created dynamically via API in this integration. No need to pre-configure rooms.

## 4. Firewall Configuration

### 4.1 Required Ports

Open the following ports on your firewall:

| Protocol | Port Range | Purpose |
|----------|------------|---------|
| TCP | 8088 | Janus HTTP API (for backend) |
| TCP | 8188 | Janus WebSocket (for browser) |
| UDP | 10000-10200 | WebRTC media (RTP/RTCP) |

### 4.2 Firewall Rules Examples

**UFW (Ubuntu)**:
```bash
sudo ufw allow 8088/tcp comment 'Janus HTTP API'
sudo ufw allow 8188/tcp comment 'Janus WebSocket'
sudo ufw allow 10000:10200/udp comment 'Janus WebRTC Media'
```

**firewalld (CentOS)**:
```bash
sudo firewall-cmd --permanent --add-port=8088/tcp
sudo firewall-cmd --permanent --add-port=8188/tcp
sudo firewall-cmd --permanent --add-port=10000-10200/udp
sudo firewall-cmd --reload
```

**iptables**:
```bash
sudo iptables -A INPUT -p tcp --dport 8088 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8188 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 10000:10200 -j ACCEPT
```

## 5. WhatsApp Settings Configuration

After Janus is running, configure your Frappe WhatsApp Settings:

### 5.1 Janus Server URLs

Navigate to: **WhatsApp Settings** > **Janus Media Server Configuration**

- **Janus HTTP API URL**: `http://YOUR_SERVER_IP:8088/janus`
  - For production with SSL: `https://your-domain.com:8089/janus`
- **Janus WebSocket URL**: `ws://YOUR_SERVER_IP:8188`
  - For production with SSL: `wss://your-domain.com:8989`

### 5.2 NAT & WebRTC Configuration

Navigate to: **WhatsApp Settings** > **NAT & WebRTC Configuration**

**Janus Public IP Address**: Enter your server's public IP
- Example: `203.0.113.42`
- This should match the `nat_1_1_mapping` value in janus.jcfg

**Enable STUN Server**: ✓ Checked (enabled by default)
- **STUN Server**: `stun.l.google.com` (Meta recommended)
- **STUN Port**: `19302`

**Enable TURN Server**: Only if needed for strict firewalls
- Leave unchecked unless you have NAT/firewall issues
- TURN servers act as relay when direct connection fails

## 6. Testing the Configuration

### 6.1 Verify Janus is Running

```bash
# Check if Janus is running
ps aux | grep janus

# Check Janus logs
tail -f /var/log/janus.log

# Test HTTP API
curl http://localhost:8088/janus
```

Expected response:
```json
{
  "janus": "server_info",
  "transaction": "..."
}
```

### 6.2 Test WebRTC Connection

1. Make a test WhatsApp call
2. Open browser console (F12)
3. Look for:
   - `ICE Configuration:` should show your STUN server
   - `Peer connection state: connected` (success)
   - Check ICE candidates include your public IP

### 6.3 Verify NAT Traversal

Check browser console for ICE candidates:
```
ICE candidate: candidate:... typ srflx raddr YOUR_PUBLIC_IP ...
```

The `raddr` should show your public IP, indicating NAT traversal is working.

## 7. Production Recommendations

### 7.1 SSL/TLS Configuration

For production, use HTTPS and WSS:

1. **Get SSL Certificate**:
   - Use Let's Encrypt: `certbot certonly --standalone -d your-domain.com`

2. **Configure Nginx/Apache as Reverse Proxy**:
   ```nginx
   # Nginx example
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

       # Proxy HTTP API
       location /janus {
           proxy_pass http://localhost:8088/janus;
           proxy_http_version 1.1;
       }

       # Proxy WebSocket
       location /janus-ws {
           proxy_pass http://localhost:8188;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

3. **Update WhatsApp Settings**:
   - Janus HTTP URL: `https://your-domain.com/janus`
   - Janus WebSocket URL: `wss://your-domain.com/janus-ws`

### 7.2 Systemd Service

Create `/etc/systemd/system/janus.service`:

```ini
[Unit]
Description=Janus WebRTC Server
After=network.target

[Service]
Type=simple
User=janus
Group=janus
WorkingDirectory=/usr/share/janus
ExecStart=/usr/share/janus/bin/janus \
    --debug-level=4 \
    --libnice-debug=off \
    -S stun.l.google.com:19302 \
    --log-file=/var/log/janus/janus.log \
    --config=/usr/share/janus/etc/janus/janus.jcfg
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable janus
sudo systemctl start janus
sudo systemctl status janus
```

### 7.3 Log Rotation

Create `/etc/logrotate.d/janus`:

```
/var/log/janus/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 janus janus
    sharedscripts
    postrotate
        systemctl reload janus > /dev/null 2>&1 || true
    endscript
}
```

### 7.4 Performance Tuning

For high-volume production:

**janus.jcfg**:
```javascript
general: {
    session_timeout = 60  # Timeout for inactive sessions
}

media: {
    rtp_port_range = "10000-10200"  # Adjust based on concurrent calls
}
```

**System limits** (`/etc/security/limits.conf`):
```
janus soft nofile 65536
janus hard nofile 65536
```

## 8. TURN Server Setup (Optional)

If you need TURN server for strict firewalls:

### 8.1 Install Coturn

```bash
# Ubuntu/Debian
sudo apt-get install coturn

# CentOS/RHEL
sudo yum install coturn
```

### 8.2 Configure Coturn

Edit `/etc/turnserver.conf`:
```
listening-port=3478
fingerprint
lt-cred-mech
use-auth-secret
static-auth-secret=YOUR_TURN_SECRET
realm=your-domain.com
total-quota=100
bps-capacity=0
stale-nonce
no-multicast-peers
```

### 8.3 Update WhatsApp Settings

Enable TURN in WhatsApp Settings:
- **Enable TURN Server**: ✓
- **TURN Server**: `your-domain.com`
- **TURN Port**: `3478`
- **TURN Username**: (generated by coturn)
- **TURN Credential**: `YOUR_TURN_SECRET`
- **TURN Transport**: `UDP`

## 9. Troubleshooting

### 9.1 WebRTC Connection Fails

**Check Janus logs**:
```bash
tail -f /var/log/janus.log | grep -i "error\|failed\|dtls"
```

**Common issues**:
- ❌ `nat_1_1_mapping` not set → WebRTC can't reach Janus
- ❌ Firewall blocking UDP ports → Media won't flow
- ❌ No STUN server → NAT traversal fails
- ❌ Wrong public IP → ICE candidates incorrect

**Solutions**:
1. Verify `nat_1_1_mapping` in janus.jcfg matches your public IP
2. Check firewall allows UDP 10000-10200
3. Ensure Janus started with `-S stun.l.google.com:19302`
4. Verify public IP with: `curl ifconfig.me`

### 9.2 DTLS Handshake Timeout

If you see: `The DTLS handshake has been completed` for WhatsApp but timeout for browser:

1. **Check browser ICE candidates**: Open browser console, look for candidates with your public IP
2. **Verify NAT configuration**: Ensure `nat_1_1_mapping` is set correctly
3. **Test connectivity**: Use `tcpdump` to verify UDP packets reaching Janus
4. **Check STUN response**: Browser should receive STUN binding responses

### 9.3 No Audio

**Symptoms**: Call connects but no audio
**Checks**:
1. Verify both WhatsApp and browser joined the same AudioBridge room
2. Check Janus logs for "WebRTC media is now available"
3. Verify browser's `ontrack` event received remote stream
4. Check browser's audio element is not muted

## 10. Architecture Overview

```
┌─────────────────┐
│ WhatsApp User   │
│   (Mobile)      │
└────────┬────────┘
         │ WebRTC (DTLS)
         │ SDP via Cloud API
         ↓
┌─────────────────────────────────────┐
│  Frappe Server                      │
│  ┌──────────────────────────────┐   │
│  │ WhatsApp Webhook Handler    │   │
│  │ (Python - SDP Negotiation)  │   │
│  └──────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │ HTTP API
               ↓
┌──────────────────────────────────────┐
│  Janus Gateway (Public IP)           │
│  ┌────────────────────────────────┐  │
│  │  AudioBridge Plugin            │  │
│  │  - Room: Dynamic per call      │  │
│  │  - Sampling: 48kHz (WhatsApp)  │  │
│  │  - Codec: Opus                 │  │
│  └────────────────────────────────┘  │
│                                      │
│  NAT: nat_1_1_mapping = PUBLIC_IP   │
│  STUN: stun.l.google.com:19302      │
└──────┬────────────────────┬──────────┘
       │                    │
       │ WebRTC (DTLS)      │ WebRTC (DTLS)
       │ UDP 10000-10200    │ UDP 10000-10200
       │                    │
┌──────▼────────┐    ┌─────▼─────────┐
│ WhatsApp      │    │ Browser Agent │
│ Caller        │    │ (Employee)    │
│ (ICE/STUN)    │    │ (ICE/STUN)    │
└───────────────┘    └───────────────┘
```

## 11. Security Considerations

1. **API Secret**: Set `admin_key` in janus.plugin.audiobridge.jcfg
2. **Firewall**: Only allow necessary ports
3. **SSL/TLS**: Use HTTPS/WSS in production
4. **Authentication**: Verify webhook signatures from Meta
5. **Rate Limiting**: Implement at reverse proxy level
6. **Log Monitoring**: Monitor for suspicious activity

## 12. References

- Meta WhatsApp Calling Integration: https://developers.facebook.com/docs/whatsapp/cloud-api/calling/integration-examples/
- Janus Gateway Documentation: https://janus.conf.meetecho.com/docs/
- Janus GitHub Repository: https://github.com/meetecho/janus-gateway
- WebRTC Best Practices: https://webrtc.org/getting-started/overview

---

**Questions or Issues?**

If you encounter issues:
1. Check Janus logs: `/var/log/janus.log`
2. Check browser console for WebRTC errors
3. Verify firewall rules
4. Ensure `nat_1_1_mapping` is set correctly
5. Test with minimal configuration first

**Support**: https://github.com/meetecho/janus-gateway/issues
