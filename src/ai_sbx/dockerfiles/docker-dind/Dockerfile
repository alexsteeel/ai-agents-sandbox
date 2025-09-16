FROM docker:28-dind

# Add custom entrypoint for registry configuration
COPY docker-dind/entrypoint.sh /usr/local/bin/docker-entrypoint-custom.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-custom.sh

# Use custom entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-custom.sh"]
CMD []