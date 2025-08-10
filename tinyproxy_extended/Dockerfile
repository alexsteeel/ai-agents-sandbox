FROM vimagick/tinyproxy:latest

# Copy default whitelist from common_settings
COPY common_settings/default-whitelist.txt /etc/tinyproxy/default-whitelist.txt

# Copy default tinyproxy configuration
COPY tinyproxy_extended/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf.default

# Create entrypoint script
COPY tinyproxy_extended/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]