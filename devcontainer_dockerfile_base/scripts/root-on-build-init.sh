#!/bin/bash

USER=claude

# Fix .claude directory ownership if it exists
if [[ -d "/home/$USER/.claude" ]]; then
    echo "Fixing .claude directory ownership..."
    chown -R $USER:$USER /home/$USER/.claude
else
    echo "Warning: /home/$USER/.claude directory not found"
fi

# Initialize firewall if the script exists
if [[ -f "/usr/local/bin/init-firewall.sh" ]]; then
    echo "Initializing firewall..."
    /usr/local/bin/init-firewall.sh -d /usr/local/etc/allowed-domains.txt
else
    echo "Warning: /usr/local/bin/init-firewall.sh not found"
fi
