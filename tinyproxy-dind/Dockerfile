FROM alpine:3.20

RUN apk add --no-cache tinyproxy

# Create tinyproxy user if it doesn't exist
RUN adduser -D -H -s /bin/false tinyproxy || true

# Copy configuration file
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && \
    mkdir -p /var/log/tinyproxy && \
    chown -R tinyproxy:tinyproxy /var/log/tinyproxy && \
    touch /etc/tinyproxy/filter && \
    chown tinyproxy:tinyproxy /etc/tinyproxy/filter

EXPOSE 8888

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]