# Deployment Guide

Complete guide for deploying the **Pune Property Price Prediction** FastAPI service on AWS EC2.

## Prerequisites

### 1. AWS EC2 Instance
- **OS**: **Ubuntu Server 24.04 LTS (Noble Numbat)** — AMI ID looks like `ami-0xxxx` and is named `ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*`
- **Architecture**: x86_64 (amd64) — the setup script and Python packages are tested on amd64; ARM64 (Graviton) works but `uvicorn[standard]` will compile some wheels from source
- **Instance Type**: t3.small or larger (2 vCPU, 2GB RAM minimum; t3.medium recommended for the voting ensemble)
- **Storage**: 20GB EBS gp3 volume
- **Security Group**: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **IMDS**: IMDSv2 is fine (the setup script uses token-based metadata calls)

### Ubuntu 24.04 quick notes
- Python 3.12 is the **default** `python3` on 24.04 — no PPA needed.
- `pip install` outside a venv is blocked by **PEP 668** (`error: externally-managed-environment`). The setup script installs everything into `.venv`, so this never trips you up.
- `needrestart` is preinstalled and will pop a TUI during `apt upgrade` — the setup script disables it for the session.
- `net-tools` is **not** installed by default, so `netstat` won't exist. Use `ss` instead (examples below).

### 2. Domain Name (Optional)
- For HTTPS/SSL certificates
- Configure DNS A record pointing to EC2 public IP

## Step-by-Step Deployment

### Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. Choose **Ubuntu Server 24.04 LTS**
3. Select **t3.medium** instance type
4. Configure Security Group:
   - SSH (22): Your IP
   - HTTP (80): 0.0.0.0/0
   - HTTPS (443): 0.0.0.0/0
5. Create/select a key pair
6. Launch instance

### Step 2: Connect to EC2

```bash
# From your local machine
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR-EC2-PUBLIC-IP
```

### Step 3: Clone Repository

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ~/pune-price-prediction-fastapi
```

#### Change File Ownership
Make sure the `ubuntu` user owns the entire application directory so the service can write logs and NLTK data.

```bash
cd ~/pune-price-prediction-fastapi
sudo chown -R ubuntu:ubuntu /home/ubuntu/pune-price-prediction-fastapi
```

### Step 4: Run Setup Script

```bash
# Make the script executable
sudo chmod +x deployment/ec2/setup.sh

# Run the automated setup
sudo deployment/ec2/setup.sh
```

The script will:
- ✅ Update system packages
- ✅ Install Python 3.12, pip, nginx, git, ufw, certbot
- ✅ Create Python virtual environment (`.venv`)
- ✅ Install all Python dependencies from `requirements.txt`
- ✅ Download NLTK corpora (`stopwords`, `punkt`, `punkt_tab`) into the project
- ✅ Verify model artifacts in `model/` exist
- ✅ Configure systemd service
- ✅ Configure NGINX (serves `frontend/` static files + proxies API)
- ✅ Configure firewall (UFW)
- ✅ Start the application

### Step 5: Verify Deployment

```bash
# Get your EC2 public IP (IMDSv2 token-based — required on most new AMIs)
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/public-ipv4

# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"API is healthy and running."}

# Test model info
curl http://localhost:8000/model/info
```

### Step 6: Access Application

Open in your browser:
- **Frontend**: `http://YOUR-EC2-IP/`
- **API Docs (Swagger)**: `http://YOUR-EC2-IP/docs`
- **ReDoc**: `http://YOUR-EC2-IP/redoc`
- **Health Check**: `http://YOUR-EC2-IP/health`
- **Model Info**: `http://YOUR-EC2-IP/model/info`

### Step 7: Smoke-Test the Predict Endpoint

```bash
curl -X POST "http://YOUR-EC2-IP/predict" \
     -H "Content-Type: application/json" \
     -d '{
           "property_type": 2,
           "area": 1200,
           "sub_area": "kothrud",
           "description": "Spacious 2 BHK apartment with modular kitchen",
           "clubhouse": 1, "school": 1, "hospital": 0,
           "mall": 0, "park": 1, "pool": 0, "gym": 1
         }'
```

## Service Management

### Check Service Status
```bash
sudo systemctl status pune-price-prediction
```

### View Logs
```bash
# Last 50 lines
sudo journalctl -u pune-price-prediction -n 50

# Follow logs in real-time
sudo journalctl -u pune-price-prediction -f

# Logs since specific time
sudo journalctl -u pune-price-prediction --since "10 minutes ago"
```

### Restart / Stop / Start
```bash
sudo systemctl restart pune-price-prediction
sudo systemctl stop    pune-price-prediction
sudo systemctl start   pune-price-prediction
```

### Disable / Enable Auto-start
```bash
sudo systemctl disable pune-price-prediction
sudo systemctl enable  pune-price-prediction
```

## NGINX Configuration

### Check NGINX Status
```bash
sudo systemctl status nginx
```

### Test NGINX Configuration
```bash
sudo nginx -t
```

### Reload NGINX
```bash
sudo systemctl reload nginx
```

### View NGINX Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/pune-price-prediction-access.log

# Error logs
sudo tail -f /var/log/nginx/pune-price-prediction-error.log
```

## SSL/HTTPS Setup (Optional)

### Using Let's Encrypt Certbot

```bash
# Install certbot (already installed by setup script)
sudo apt install certbot python3-certbot-nginx -y

# Edit NGINX config to add your domain
sudo nano /etc/nginx/sites-available/pune-price-prediction
# Change: server_name _;
# To:     server_name yourdomain.com www.yourdomain.com;

# Test configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Auto-renewal
```bash
sudo certbot renew --dry-run
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u pune-price-prediction -n 100 --no-pager

# Common issues:
# 1. Port 8000 already in use
# 2. Missing model/*.pkl or .sav artifacts
# 3. NLTK data not found (stopwords / punkt / punkt_tab)
# 4. File permissions on /home/ubuntu/pune-price-prediction-fastapi
# 5. Wrong working directory (must be project root, not src/)
```

### `ModuleNotFoundError: No module named 'src'`
The systemd service must run uvicorn from the **project root** (`/home/ubuntu/pune-price-prediction-fastapi`), not from inside `src/`. Verify `WorkingDirectory=` in `pune-price-prediction.service`.

### `LookupError: Resource 'punkt_tab' not found`
Re-run the NLTK download:
```bash
sudo -u ubuntu NLTK_DATA=/home/ubuntu/pune-price-prediction-fastapi/nltk_data \
    /home/ubuntu/pune-price-prediction-fastapi/.venv/bin/python \
    -m nltk.downloader -d /home/ubuntu/pune-price-prediction-fastapi/nltk_data \
    stopwords punkt punkt_tab
sudo systemctl restart pune-price-prediction
```

### Check Port Availability
On Ubuntu 24.04 the `netstat` tool isn't installed by default. Use `ss` instead:
```bash
sudo ss -tlnp | grep :8000
# Kill if needed:
sudo kill -9 <PID>

# (Optional) install net-tools if you really want netstat:
# sudo apt-get install -y net-tools
```

### Fix File Permissions
```bash
sudo chown -R ubuntu:ubuntu /home/ubuntu/pune-price-prediction-fastapi
sudo chmod o+x /home/ubuntu
sudo chmod -R o+rX /home/ubuntu/pune-price-prediction-fastapi/frontend
```

### Reinstall Dependencies
```bash
cd ~/pune-price-prediction-fastapi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend 404 Error

```bash
# Check frontend files exist
ls -la ~/pune-price-prediction-fastapi/frontend/

# Verify NGINX config
sudo nano /etc/nginx/sites-available/pune-price-prediction

# The location / block should point to:
# root /home/ubuntu/pune-price-prediction-fastapi/frontend;

sudo nginx -t
sudo systemctl reload nginx
```

### Frontend Loads But Predictions Fail
The frontend's `script.js` may be calling `http://127.0.0.1:8000`. After deploying behind NGINX, change the API base URL in `frontend/script.js` to a relative path (e.g. `/predict`) so it goes through NGINX on port 80.

## Updating the Application

```bash
# Stop service
sudo systemctl stop pune-price-prediction

# Pull latest changes
cd ~/pune-price-prediction-fastapi
git pull origin main

# Reinstall dependencies if requirements changed (must be inside .venv —
# Ubuntu 24.04 blocks system-wide pip installs via PEP 668)
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start pune-price-prediction
```

## Monitoring

### Check System Resources
```bash
htop                # CPU and Memory
df -h               # Disk usage
ps aux | grep uvicorn
```

### Application Metrics
```bash
# Request count from NGINX logs
sudo cat /var/log/nginx/pune-price-prediction-access.log | wc -l

# Recent errors
sudo tail -n 50 /var/log/nginx/pune-price-prediction-error.log
```

## Backup

### Backup Model Artifacts
```bash
tar -czf model-backup-$(date +%Y%m%d).tar.gz ~/pune-price-prediction-fastapi/model/
```

## Clean Deployment (Starting Fresh)

```bash
# Stop and remove everything
sudo systemctl stop pune-price-prediction
sudo systemctl disable pune-price-prediction
sudo rm -f /etc/systemd/system/pune-price-prediction.service
sudo rm -f /etc/nginx/sites-enabled/pune-price-prediction
sudo rm -f /etc/nginx/sites-available/pune-price-prediction
sudo systemctl daemon-reload
sudo rm -rf ~/pune-price-prediction-fastapi

# Then follow deployment steps from Step 3
```

## Security Best Practices

1. **Limit SSH Access**: Restrict Security Group port 22 to your IP only
2. **Regular Updates**: `sudo apt update && sudo apt upgrade -y`
3. **Enable HTTPS**: Use SSL/TLS for production via Certbot
4. **Firewall**: UFW is enabled by the setup script
5. **CORS**: `app.py` currently allows all origins (`*`) for dev — tighten to your domain in production
6. **Monitoring**: Set up CloudWatch or similar
7. **Backups**: Regular backups of model artifacts and NGINX config

## Cost Optimization

- Use **t3.small** for low-traffic demos
- Scale to **t3.medium** or **t3.large** for production traffic
- Consider **Spot Instances** for dev/test environments
- Use **Elastic IP** to keep the same public IP across reboots

## Support

For issues or questions:
- Check logs: `sudo journalctl -u pune-price-prediction -f`
- Check NGINX: `sudo tail -f /var/log/nginx/pune-price-prediction-error.log`
- Open a GitHub issue

---

**Last Updated**: April 2026
