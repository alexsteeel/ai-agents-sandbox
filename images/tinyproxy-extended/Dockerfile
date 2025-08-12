FROM vimagick/tinyproxy:latest

# Copy default whitelist from common_settings
COPY images/common-settings/default-whitelist.txt /etc/tinyproxy/default-whitelist.txt

# Copy default tinyproxy configuration
COPY images/tinyproxy-extended/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf.default

# Create entrypoint script
COPY images/tinyproxy-extended/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]