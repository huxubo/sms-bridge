        #!/bin/bash
        set -e
        echo "Copying files to /opt/sms-bridge..."
        sudo mkdir -p /opt/sms-bridge
        sudo cp -r . /opt/sms-bridge
        sudo bash -c 'cat > /etc/systemd/system/sms-bridge.service <<"EOF"
[Unit]
Description=SMS-Bridge
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=/opt/sms-bridge
ExecStart=/usr/bin/python3 /opt/sms-bridge/app/web.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF'
        sudo systemctl daemon-reload
        sudo systemctl enable --now sms-bridge.service
