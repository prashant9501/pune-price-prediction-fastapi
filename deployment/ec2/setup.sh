#!/bin/bash
#
# Pune Property Price Prediction - EC2 Deployment Setup Script
# This script automates the deployment on AWS EC2 Ubuntu 24.04 LTS
#
# Usage: sudo ./setup.sh
#

set -e  # Exit on error

# --- Ubuntu 24.04 LTS non-interactive apt settings ---
# 24.04 ships `needrestart` by default which prompts during apt operations and
# breaks automated installs. Suppress all interactive prompts for this session.
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a       # automatically restart services
export NEEDRESTART_SUSPEND=1    # don't interrupt apt with the TUI prompt
APT_OPTS=(-y \
    -o Dpkg::Options::=--force-confdef \
    -o Dpkg::Options::=--force-confold)

echo "=========================================="
echo "Pune Price Prediction - EC2 Setup"
echo "Target OS: Ubuntu 24.04 LTS (Noble Numbat)"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_info "Starting deployment setup..."

# Update system
print_info "Updating apt metadata and upgrading installed packages..."
apt-get update
apt-get "${APT_OPTS[@]}" upgrade
print_success "System updated"

# Install dependencies
# Note: Ubuntu 24.04 ships Python 3.12 as the default `python3`, so most of
# these are already present — apt-get will be a no-op for those.
print_info "Installing system dependencies..."
apt-get "${APT_OPTS[@]}" install \
    python3.12 \
    python3.12-venv \
    python3-pip \
    nginx \
    git \
    curl \
    ufw \
    certbot \
    python3-certbot-nginx
print_success "Dependencies installed"

# Application directory
APP_DIR="/home/ubuntu/pune-price-prediction-fastapi"
print_info "Setting up application directory: $APP_DIR"

if [ ! -d "$APP_DIR" ]; then
    print_info "Application directory not found. Please clone the repository first."
    print_info "Run: git clone <your-repo-url> $APP_DIR"
    exit 1
fi

# Ensure ubuntu user owns the project (so the service can write logs / NLTK data)
chown -R ubuntu:ubuntu "$APP_DIR"

cd "$APP_DIR"

# Create virtual environment as the ubuntu user
print_info "Creating Python virtual environment..."
sudo -u ubuntu python3.12 -m venv .venv
print_success "Virtual environment created"

# Install Python dependencies
print_info "Installing Python packages..."
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install -r requirements.txt
print_success "Python packages installed"

# Download NLTK data into the project (used by src/inference.py)
print_info "Downloading NLTK data (stopwords, punkt, punkt_tab)..."
sudo -u ubuntu mkdir -p "$APP_DIR/nltk_data"
sudo -u ubuntu NLTK_DATA="$APP_DIR/nltk_data" \
    "$APP_DIR/.venv/bin/python" -m nltk.downloader \
        -d "$APP_DIR/nltk_data" \
        stopwords punkt punkt_tab
print_success "NLTK data downloaded"

# Verify model artifacts exist
print_info "Verifying model artifacts..."
if [ ! -f "$APP_DIR/model/property_price_prediction_voting.sav" ]; then
    print_error "Model file missing: model/property_price_prediction_voting.sav"
    print_info "Make sure all .pkl/.sav artifacts are present in the model/ directory"
    exit 1
fi
print_success "Model artifacts present"

# Setup systemd service
print_info "Setting up systemd service..."
cp deployment/ec2/systemd/pune-price-prediction.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable pune-price-prediction
print_success "Systemd service configured"

# Start the service
print_info "Starting pune-price-prediction service..."
systemctl start pune-price-prediction
print_success "Service started"

# Configure NGINX
print_info "Configuring NGINX..."
cp deployment/ec2/nginx/sites-available/pune-price-prediction /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/pune-price-prediction /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
print_success "NGINX configured"

# Allow nginx to read the frontend directory
chmod o+x /home/ubuntu
chmod -R o+rX "$APP_DIR/frontend"

# Configure firewall
print_info "Configuring UFW firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
print_success "Firewall configured"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check status: sudo systemctl status pune-price-prediction"
echo "2. View logs:    sudo journalctl -u pune-price-prediction -f"
echo "3. Test health:  curl http://localhost:8000/health"
echo ""

# Use IMDSv2 (token-based) — required on most new EC2 AMIs (Ubuntu 24.04
# launches usually default to IMDSv2-only, where IMDSv1 calls return 401).
IMDS_TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true)
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
    http://169.254.169.254/latest/meta-data/public-ipv4 || echo "<EC2-PUBLIC-IP>")
echo "Access your application at: http://$PUBLIC_IP"
echo ""
