# WhatsApp Calling - Detailed Installation Guide

This guide provides step-by-step instructions for installing and configuring the WhatsApp Calling app.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install Janus Gateway](#install-janus-gateway)
3. [Install Frappe App](#install-frappe-app)
4. [Configure WhatsApp Business API](#configure-whatsapp-business-api)
5. [Configure the App](#configure-the-app)
6. [Verify Installation](#verify-installation)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB+
- **Network**: Public IP with open ports (for webhooks)

### Software Requirements

- **Frappe**: v15.0.0 or higher
- **ERPNext**: v15.0.0 or higher
- **Python**: 3.10+
- **Node.js**: 16+
- **MariaDB**: 10.6+ or PostgreSQL 12+
- **Redis**: 6+

## Install Janus Gateway

### Option 1: Docker (Recommended for Development)

```bash
# Pull official Janus Docker image
docker pull canyan/janus-gateway:latest

# Run Janus container
docker run -d \
  --name janus-gateway \
  --restart unless-stopped \
  -p 8088:8088 \
  -p 8089:8089 \
  -p 8188:8188 \
  -p 8989:8989 \
  -p 20000-20100:20000-20100/udp \
  -e JANUS_API_HTTPS=yes \
  -e JANUS_API_WSS=yes \
  canyan/janus-gateway:latest

# Verify Janus is running
curl http://localhost:8088/janus/info

# Check logs
docker logs janus-gateway
```

### Option 2: Manual Installation (Production)

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y \
    libmicrohttpd-dev \
    libjansson-dev \
    libssl-dev \
    libsrtp2-dev \
    libsofia-sip-ua-dev \
    libglib2.0-dev \
    libopus-dev \
    libogg-dev \
    libcurl4-openssl-dev \
    liblua5.3-dev \
    libconfig-dev \
    pkg-config \
    gengetopt \
    libtool \
    automake \
    cmake \
    git

# Clone Janus repository
cd /opt
sudo git clone https://github.com/meetecho/janus-gateway.git
cd janus-gateway

# Generate configure script
sudo sh autogen.sh

# Configure with required plugins
sudo ./configure --prefix=/opt/janus \
    --enable-websockets \
    --enable-rest \
    --enable-plugin-audiobridge \
    --enable-plugin-recordplay

# Build
sudo make

# Install
sudo make install

# Create config files
sudo make configs

# Create systemd service
sudo tee /etc/systemd/system/janus.service > /dev/null <<EOF
[Unit]
Description=Janus WebRTC Server
After=network.target

[Service]
Type=simple
ExecStart=/opt/janus/bin/janus
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable janus
sudo systemctl start janus
sudo systemctl status janus
```

### Configure Janus for Production

```bash
# Edit main config
sudo nano /opt/janus/etc/janus/janus.jcfg

# Set API secret
api_secret = "your-secure-random-secret"

# Edit HTTP transport
sudo nano /opt/janus/etc/janus/janus.transport.http.jcfg

# Enable HTTPS
https = true
secure_port = 8089
cert_pem = "/path/to/certificate.pem"
cert_key = "/path/to/private.key"

# Edit WebSocket transport
sudo nano /opt/janus/etc/janus/janus.transport.websockets.jcfg

# Enable WSS
wss_port = 8989
wss_interface = "0.0.0.0"
wss_ip = "your.domain.com"

# Edit AudioBridge plugin
sudo nano /opt/janus/etc/janus/janus.plugin.audiobridge.jcfg

# Configure recording path
rec_dir = "/var/janus/recordings"

# Create recording directory
sudo mkdir -p /var/janus/recordings
sudo chown -R janus:janus /var/janus

# Restart Janus
sudo systemctl restart janus
```

### Setup SSL Certificates (Production)

```bash
# Install Certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d janus.yourdomain.com

# Certificate will be at:
# /etc/letsencrypt/live/janus.yourdomain.com/

# Setup auto-renewal
sudo crontab -e

# Add this line:
0 3 * * * certbot renew --quiet && systemctl restart janus
```

## Install Frappe App

```bash
# Navigate to frappe-bench
cd ~/frappe-bench

# Get app from GitHub
bench get-app https://github.com/your-username/whatsapp-calling.git

# Or from local directory
# bench get-app /path/to/whatsapp-calling

# Install on site
bench --site your-site-name install-app whatsapp_calling

# Migrate database
bench --site your-site-name migrate

# Clear cache
bench --site your-site-name clear-cache

# Build assets
bench build --app whatsapp_calling

# Restart bench
bench restart
```

## Configure WhatsApp Business API

### Step 1: Create Meta App

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Click "My Apps" > "Create App"
3. Select "Business" type
4. Fill in app details
5. Click "Create App"

### Step 2: Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set Up"
3. Follow the setup wizard

### Step 3: Get Phone Number

1. Navigate to WhatsApp > Getting Started
2. Click "Add Phone Number"
3. Verify your business phone number
4. Note the **Phone Number ID**

### Step 4: Get Access Token

1. Navigate to WhatsApp > Getting Started
2. Find "Temporary access token"
3. Copy the token
4. For production, generate a permanent token

### Step 5: Setup Webhook

1. Navigate to WhatsApp > Configuration
2. Edit Webhook
3. Callback URL: `https://yoursite.com/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook`
4. Verify Token: Create a random string (save it for later)
5. Click "Verify and save"
6. Subscribe to field: `calls`

### Step 6: Create Message Template

1. Navigate to WhatsApp > Message Templates
2. Click "Create Template"
3. Template Name: `call_permission_request`
4. Category: Utility
5. Language: English
6. Content:
```
Hello! We'd like to call you to discuss your inquiry.
Do you give us permission to call you on WhatsApp?
```
7. Add Button: "Voice Call Request"
8. Submit for approval (usually takes 24-48 hours)

## Configure the App

### Step 1: Configure WhatsApp Settings

```bash
# Login to your Frappe site
bench --site your-site-name browse
```

1. Navigate to: **Setup > WhatsApp Calling > WhatsApp Settings**

2. **WhatsApp API Configuration:**
   - Default Access Token: `paste-your-token-here`
   - Webhook Verify Token: `same-as-meta-webhook-token`

3. **Janus Media Server Configuration:**
   - Janus HTTP API URL: `http://localhost:8088/janus` (dev) or `https://janus.yourdomain.com:8089/janus` (prod)
   - Janus WebSocket URL: `ws://localhost:8188` (dev) or `wss://janus.yourdomain.com:8989` (prod)
   - Janus API Secret: `your-janus-api-secret`

4. **Call Recording Settings:**
   - ✓ Enable Call Recording
   - Recording Storage Path: `/recordings`
   - Recording Format: Opus
   - Retention Days: 90

5. Click **Save**

### Step 2: Add WhatsApp Number

1. Navigate to: **WhatsApp Calling > WhatsApp Number > New**

2. Fill in:
   - Phone Number: `+919876543210` (must match Meta registered number)
   - Display Name: `Your Business Name`
   - Company: Select company
   - Status: Active
   - Phone Number ID: `paste-from-meta`
   - Business Account ID: `your-waba-id`
   - Access Token: Leave blank to use default

3. Click **Save**

### Step 3: Configure Firewall

```bash
# Allow Janus ports
sudo ufw allow 8088/tcp
sudo ufw allow 8089/tcp
sudo ufw allow 8188/tcp
sudo ufw allow 8989/tcp
sudo ufw allow 20000:20100/udp

# Reload firewall
sudo ufw reload
```

## Verify Installation

### Test 1: Janus Connection

```bash
curl http://localhost:8088/janus/info
```

Expected output:
```json
{
  "janus": "server_info",
  "name": "Janus WebRTC Server",
  "version": ...,
  "plugins": {...}
}
```

### Test 2: Webhook Verification

```bash
curl -X GET "https://yoursite.com/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test"
```

Expected output: `test`

### Test 3: WhatsApp Settings

1. Open WhatsApp Settings in Frappe
2. Click "Test Janus Connection"
3. Should show success message

### Test 4: Make Test Call

1. Create a test Lead with mobile number
2. Click "📞 > Request Call Permission"
3. On your phone, grant permission
4. Click "📞 > WhatsApp Call"
5. Allow microphone in browser
6. Call should connect

## Troubleshooting

### Janus Not Starting

```bash
# Check logs
sudo journalctl -u janus -f

# Check if port is in use
sudo netstat -tulpn | grep 8088

# Verify config syntax
/opt/janus/bin/janus --check-config
```

### Webhook Not Working

1. Check webhook is publicly accessible:
```bash
curl https://yoursite.com/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook
```

2. Check Frappe logs:
```bash
bench --site your-site-name logs
```

3. Verify SSL certificate (webhooks require HTTPS)

### Audio Not Working

1. Check browser console for WebRTC errors
2. Verify microphone permissions
3. Test on different browser
4. Check Janus AudioBridge plugin is loaded
5. For production, ensure HTTPS (WebRTC requires secure context)

### Permission Request Not Sending

1. Verify template is approved in Meta
2. Check template name matches exactly
3. Verify access token is valid
4. Check Frappe error logs

## Next Steps

- [Read the User Guide](README.md#usage)
- [Configure scheduled tasks](README.md#scheduled-tasks)
- [Setup SSL for production](README.md#janus-configuration-production)
- [Join the community](https://github.com/your-username/whatsapp-calling/discussions)

## Support

If you encounter issues:
1. Check [Troubleshooting](README.md#troubleshooting)
2. Search [existing issues](https://github.com/your-username/whatsapp-calling/issues)
3. Create a [new issue](https://github.com/your-username/whatsapp-calling/issues/new)
