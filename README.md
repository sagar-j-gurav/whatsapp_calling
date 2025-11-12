# WhatsApp Calling - Frappe Custom App

A comprehensive Frappe v15 custom app that enables businesses to make and receive voice calls through WhatsApp Business API directly from their ERPNext CRM Lead forms.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Frappe Version](https://img.shields.io/badge/Frappe-v15-blue)](https://frappeframework.com)

## 🎯 Features

- **📞 WhatsApp Voice Calling**: Make and receive calls via WhatsApp Business API
- **🔗 CRM Integration**: Seamless integration with ERPNext Lead doctype
- **🎙️ WebRTC Audio**: Browser-based calling using WebRTC technology
- **📊 Call Recording**: Automatic recording of all calls with configurable retention
- **✅ Permission Management**: WhatsApp-compliant call permission system
- **💰 Cost Tracking**: Automatic calculation and tracking of call costs
- **👥 Multi-Tenancy**: Support for multiple companies with separate phone numbers
- **📈 Call Analytics**: Comprehensive call history and statistics
- **🔔 Real-time Notifications**: Instant alerts for incoming calls

## 🏗️ Architecture

```
WhatsApp User ↔ Meta WhatsApp Cloud API ↔ Frappe App ↔ Janus Media Server ↔ Agent Browser (WebRTC)
```

### Key Components

1. **Frappe Backend (Python)**: Handles webhooks, call management, permissions
2. **Janus Gateway (Media Server)**: Bridges WhatsApp audio ↔ Browser WebRTC
3. **Frontend (JavaScript)**: WebRTC client in Frappe UI
4. **Database**: Frappe Doctypes for call records, numbers, permissions

## 📋 Prerequisites

### 1. Frappe/ERPNext Setup
- Frappe v15 or higher
- ERPNext installed
- Python 3.10+
- MariaDB/PostgreSQL

### 2. Janus Gateway Media Server

**Quick Docker Installation (Recommended for Development)**
```bash
docker pull canyan/janus-gateway:latest

docker run -d \
  --name janus-gateway \
  -p 8088:8088 \
  -p 8089:8089 \
  -p 8188:8188 \
  -p 8989:8989 \
  -p 20000-20100:20000-20100/udp \
  canyan/janus-gateway:latest
```

**Verify Installation**
```bash
curl http://localhost:8088/janus/info
```

### 3. WhatsApp Business API
- Meta Business Account
- WhatsApp Business API access
- Phone Number registered with Meta
- Access Token and Webhook Verify Token

## 🚀 Installation

### Step 1: Install the App

```bash
# Navigate to your frappe-bench
cd ~/frappe-bench

# Get the app from repository
bench get-app https://github.com/your-username/whatsapp-calling.git

# Install on your site
bench --site [your-site-name] install-app whatsapp_calling

# Migrate database
bench --site [your-site-name] migrate

# Build assets
bench build --app whatsapp_calling

# Restart bench
bench restart
```

### Step 2: Configure WhatsApp Settings

1. Navigate to: **Setup > WhatsApp Calling > WhatsApp Settings**

2. Configure the following:

**WhatsApp API Configuration:**
- Default Access Token: Your Meta WhatsApp Business API token
- Webhook Verify Token: Token for webhook verification

**Janus Media Server Configuration:**
- Janus HTTP API URL: `http://localhost:8088/janus`
- Janus WebSocket URL: `ws://localhost:8188` (dev) or `wss://janus.yourdomain.com:8989` (prod)
- Janus API Secret: (from your janus.jcfg file)

**Call Recording Settings:**
- Enable Call Recording: ✓
- Recording Storage Path: `/recordings`
- Recording Format: Opus
- Retention Days: 90

3. Click **Save**

### Step 3: Add WhatsApp Business Number

1. Navigate to: **WhatsApp Calling > WhatsApp Number > New**

2. Fill in details:
- Phone Number: `+919876543210` (E.164 format)
- Display Name: Your Business Name
- Company: Select your company
- Status: Active
- Phone Number ID: (from Meta Business Manager)
- Access Token: (optional, uses default if blank)

3. Click **Save**

### Step 4: Configure Meta Webhook

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Select your app
3. Navigate to WhatsApp > Configuration
4. Add Webhook URL: `https://yoursite.com/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook`
5. Add Verify Token: (same as in WhatsApp Settings)
6. Subscribe to field: `calls`
7. Save

## 📖 Usage

### Making Outbound Calls from CRM Lead

1. Open a **Lead** record
2. Ensure mobile number is filled
3. Click **"📞 > WhatsApp Call"** button
4. Confirm the call
5. Allow microphone access when prompted
6. Call will be initiated

### Request Call Permission (First Time)

1. Open a **Lead** record
2. Click **"📞 > Request Call Permission"**
3. Customer receives WhatsApp template message
4. Once customer grants permission, you can call

### Answering Incoming Calls

1. When a call comes in, you'll see a popup notification
2. Click **"Answer"** to accept the call
3. Click **"Decline"** to reject

### Call Controls

During an active call:
- **Mute**: Toggle microphone on/off
- **End Call**: Terminate the call
- **Timer**: Shows call duration

### View Call History

1. Navigate to: **WhatsApp Calling > WhatsApp Call**
2. Filter by Lead, Company, Date, etc.
3. Click on a call to view details
4. Play recordings (if enabled)

## 🔧 Configuration

### Janus Configuration (Production)

For production, enable SSL/TLS:

```bash
# Edit Janus HTTP transport config
sudo nano /opt/janus/etc/janus/janus.transport.http.jcfg

# Enable HTTPS
https = true
secure_port = 8089

# Add SSL certificates
cert_pem = "/etc/letsencrypt/live/janus.yourdomain.com/cert.pem"
cert_key = "/etc/letsencrypt/live/janus.yourdomain.com/privkey.pem"

# Restart Janus
sudo systemctl restart janus
```

### WhatsApp Template (Call Permission Request)

Create a template in Meta Business Manager:

**Template Name**: `call_permission_request`

**Content**:
```
Hello! We'd like to call you to discuss your inquiry.
Do you give us permission to call you on WhatsApp?

[Button: Voice Call Request]
```

### Scheduled Tasks

The app includes automated tasks:

- **Hourly**: Cleanup old recordings, cleanup stale Janus rooms
- **Daily**: Check expired permissions, reset daily counters, send summary email
- **Monthly**: Reset monthly usage counters

Configure in `hooks.py`:
```python
scheduler_events = {
    "hourly": [
        "whatsapp_calling.whatsapp_calling.tasks.cleanup_old_recordings",
        "whatsapp_calling.whatsapp_calling.tasks.cleanup_stale_janus_rooms"
    ],
    "daily": [
        "whatsapp_calling.whatsapp_calling.tasks.check_expired_permissions",
        "whatsapp_calling.whatsapp_calling.tasks.reset_daily_counters"
    ]
}
```

## 📁 Project Structure

```
whatsapp_calling/
├── whatsapp_calling/
│   ├── whatsapp_calling/
│   │   ├── doctype/
│   │   │   ├── whatsapp_call/          # Call records
│   │   │   ├── whatsapp_number/        # Business numbers
│   │   │   ├── whatsapp_settings/      # Global settings
│   │   │   └── call_permission/        # Permission tracking
│   │   ├── api/
│   │   │   ├── webhook.py              # WhatsApp webhook handler
│   │   │   ├── call_control.py         # Call operations
│   │   │   ├── permissions.py          # Permission management
│   │   │   └── janus_client.py         # Janus integration
│   │   ├── utils/
│   │   │   ├── whatsapp_api.py         # WhatsApp API wrapper
│   │   │   └── validators.py           # Validation utilities
│   │   └── tasks.py                    # Background jobs
│   ├── public/
│   │   ├── js/
│   │   │   ├── whatsapp_call_widget.js # WebRTC client
│   │   │   └── lead_call_button.js     # CRM integration
│   │   └── css/
│   │       └── whatsapp_calling.css    # Styling
│   └── hooks.py                        # App configuration
├── requirements.txt
├── setup.py
└── README.md
```

## 🔐 Security & Permissions

### Call Permission System

WhatsApp requires explicit permission before making outbound calls:

- **Permission Request Limits**:
  - 1 request per 24 hours
  - 2 requests per 7 days
- **Permission Validity**: 7 days after grant
- **Call Limits**: 5 calls per 24 hours after permission granted

### User Permissions

Configure in Frappe:

**System Manager**: Full access to all doctypes
**Sales User**: Can make calls, view their company's calls

## 💰 Pricing & Costs

### WhatsApp API Pricing (Approximate)

- **Inbound Calls**: Free
- **Outbound Calls**: ~$0.01 - $0.05 per minute (varies by country)

### Cost Tracking

The app automatically calculates and tracks:
- Per-call costs
- Daily usage
- Monthly budgets
- Company-wise spending

## 🐛 Troubleshooting

### Janus Connection Failed

```bash
# Check if Janus is running
curl http://localhost:8088/janus/info

# Check Janus logs
docker logs janus-gateway

# Verify ports are open
netstat -tulpn | grep 8088
```

### Webhook Not Receiving Events

1. Verify webhook URL is accessible publicly
2. Check Meta webhook configuration
3. Verify webhook verify token matches
4. Check Frappe error logs: `bench --site [site] logs`

### No Audio During Call

1. Check microphone permissions in browser
2. Verify Janus WebSocket connection
3. Check browser console for WebRTC errors
4. Ensure HTTPS for production (WebRTC requires secure context)

### Call Permission Not Working

1. Verify WhatsApp template is approved in Meta
2. Check template name matches exactly
3. Verify business number is verified with Meta
4. Check error logs for API errors

## 📊 API Reference

### Make Call

```python
frappe.call({
    method: 'whatsapp_calling.whatsapp_calling.api.call_control.make_call',
    args: {
        lead_name: 'LEAD-001',
        mobile_number: '+919876543210'
    }
})
```

### Answer Call

```python
frappe.call({
    method: 'whatsapp_calling.whatsapp_calling.api.call_control.answer_call',
    args: {
        call_id: 'wamid.xxxxx'
    }
})
```

### End Call

```python
frappe.call({
    method: 'whatsapp_calling.whatsapp_calling.api.call_control.end_call',
    args: {
        call_id: 'wamid.xxxxx'
    }
})
```

### Request Permission

```python
frappe.call({
    method: 'whatsapp_calling.whatsapp_calling.api.permissions.request_call_permission',
    args: {
        lead_name: 'LEAD-001',
        mobile_number: '+919876543210'
    }
})
```

## 🧪 Testing

### Test Janus Connection

```bash
curl -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus": "create", "transaction": "test123"}'
```

### Test Webhook

```bash
curl -X GET "https://yoursite.com/api/method/whatsapp_calling.whatsapp_calling.api.webhook.whatsapp_webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test"
```

### Test WhatsApp API

```bash
curl -X POST "https://graph.facebook.com/v18.0/PHONE_NUMBER_ID/calls" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to": "+919876543210", "type": "voice"}'
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](license.txt) file for details.

## 🙏 Credits

- **Frappe Framework**: https://frappeframework.com
- **Janus Gateway**: https://janus.conf.meetecho.com
- **WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp

## 📧 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/your-username/whatsapp-calling/issues)
- Email: support@example.com
- Documentation: [Wiki](https://github.com/your-username/whatsapp-calling/wiki)

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Basic calling from CRM Lead
- ✅ Call recording
- ✅ Permission management
- ✅ Janus integration

### Phase 2 (Planned)
- [ ] Call queue management
- [ ] IVR (Interactive Voice Response)
- [ ] Call transfers
- [ ] Conference calls
- [ ] SMS integration

### Phase 3 (Future)
- [ ] AI-powered call insights
- [ ] Automatic transcription
- [ ] Sentiment analysis
- [ ] Integration with other CRM modules

## 📈 Changelog

### v0.0.1 (2024-11-07)
- Initial release
- Basic calling functionality
- CRM Lead integration
- Permission management
- Call recording
- Janus Gateway integration

---

Made with ❤️ for the Frappe/ERPNext community
