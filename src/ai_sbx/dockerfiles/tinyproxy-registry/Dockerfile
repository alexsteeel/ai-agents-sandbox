ARG IMAGE_TAG=latest
FROM ai-agents-sandbox/tinyproxy-base:${IMAGE_TAG}

COPY tinyproxy-registry/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY tinyproxy-registry/default-registry-whitelist.txt /usr/local/share/tinyproxy/default-registry-whitelist.txt
COPY tinyproxy-registry/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chown -R tinyproxy:tinyproxy /etc/tinyproxy && \
    chmod 755 /etc/tinyproxy && \
    mkdir -p /usr/local/share/tinyproxy && \
    chmod 755 /usr/local/share/tinyproxy
USER tinyproxy

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]