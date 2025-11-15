#!/bin/bash
# Janus Gateway startup script for macOS Docker development
# This script configures NAT traversal properly for local testing

# Stop and remove existing container
docker stop janus-gateway 2>/dev/null
docker rm janus-gateway 2>/dev/null

# Get the Mac's public IP address (for NAT mapping)
# This uses a STUN-like service to detect your public IP
PUBLIC_IP=$(curl -s https://api.ipify.org)

echo "========================================="
echo "Starting Janus Gateway for Mac Development"
echo "========================================="
echo "Public IP detected: $PUBLIC_IP"
echo "This IP will be advertised in ICE candidates"
echo ""

# Run Janus with proper NAT configuration
docker run -d \
  --name janus-gateway \
  --platform linux/amd64 \
  -p 8088:8088 \
  -p 8188:8188 \
  -p 7088:7088 \
  -p 10000-10200:10000-10200/udp \
  -e DOCKER_IP="$PUBLIC_IP" \
  canyan/janus-gateway:latest \
  /bin/bash -c "
    # Start Janus with NAT 1:1 mapping to public IP
    /usr/local/bin/janus \
      --configs-folder=/usr/local/etc/janus \
      --nat-1-1=$PUBLIC_IP \
      --stun-server=stun.l.google.com:19302 \
      --debug-level=5
  "

echo ""
echo "Waiting for Janus to start..."
sleep 5

# Verify Janus is running
if curl -s http://localhost:8088/janus > /dev/null; then
    echo "✓ Janus is running successfully!"
    echo ""
    echo "Configuration:"
    echo "  - HTTP API: http://localhost:8088/janus"
    echo "  - WebSocket: ws://localhost:8188"
    echo "  - NAT 1:1 mapping: $PUBLIC_IP"
    echo "  - STUN server: stun.l.google.com:19302"
    echo ""
    echo "You can now make WhatsApp calls!"
else
    echo "✗ Error: Janus failed to start"
    echo "Check logs with: docker logs janus-gateway"
    exit 1
fi
