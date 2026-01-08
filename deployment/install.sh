#!/bin/bash

# Health Monitor - Installation Script
# Installs all components on a clean Ubuntu/Debian system

set -e  # Exit on error

echo "🚀 Health Monitor - Installation Script"
echo "========================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root" 
   exit 1
fi

# Variables
INSTALL_DIR="/opt/health-monitor"
SERVICE_USER="health-monitor"
DOMAIN="monitor.example.com"  # Change this

echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nodejs npm nginx certbot python3-certbot-nginx docker.io docker-compose git

echo "👤 Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false $SERVICE_USER
    echo "✅ User $SERVICE_USER created"
else
    echo "ℹ️  User $SERVICE_USER already exists"
fi

echo "📂 Creating installation directory..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

echo "📥 Cloning repository..."
git clone https://github.com/Kirachon/health_check.git .

echo "🐍 Setting up Python virtual environments..."

# Server
cd $INSTALL_DIR/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Agent
cd $INSTALL_DIR/agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "⚙️  Configuring server..."
cd $INSTALL_DIR/server
cp .env.example .env
# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)
sed -i "s/your-secret-key-change-in-production-minimum-32-characters/$SECRET_KEY/" .env

echo "🐳 Starting Docker services..."
cd $INSTALL_DIR
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

echo "🔧 Setting up systemd services..."
cp deployment/systemd/health-monitor-api.service /etc/systemd/system/
cp deployment/systemd/health-monitor-agent.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable health-monitor-api
systemctl enable health-monitor-agent
systemctl start health-monitor-api
systemctl start health-monitor-agent

echo "🌐 Configuring Nginx..."
cp deployment/nginx/health-monitor.conf /etc/nginx/sites-available/
sed -i "s/monitor.example.com/$DOMAIN/g" /etc/nginx/sites-available/health-monitor.conf
ln -sf /etc/nginx/sites-available/health-monitor.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "🔒 Setting up SSL with Let's Encrypt..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

echo "🔐 Setting file permissions..."
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chmod -R 750 $INSTALL_DIR

echo ""
echo "✅ Installation complete!"
echo ""
echo "Services:"
echo "  - API: https://$DOMAIN/api/v1/docs"
echo "  - GUI: https://$DOMAIN"
echo "  - Grafana: https://$DOMAIN/grafana"
echo ""
echo "Admin bootstrap:"
echo "  - Create the first admin via scripts/create_admin.py"
echo ""
echo "Next steps:"
echo "  1. Create the admin account"
echo "  2. Configure agent on monitored devices"
echo "  3. Set up email + internal webhook notifications in Grafana"
echo ""
echo "Service status:"
systemctl status health-monitor-api --no-pager
systemctl status health-monitor-agent --no-pager
