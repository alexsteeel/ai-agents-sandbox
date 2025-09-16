FROM alpine:3.20
RUN apk add --no-cache tinyproxy
RUN adduser -D -H -s /bin/false tinyproxy || true
# Set proper permissions for tinyproxy user to write configuration
RUN chown -R tinyproxy:tinyproxy /etc/tinyproxy && \
    chmod 755 /etc/tinyproxy
