FROM confluentinc/cp-kafka-connect:7.6.0

# Install Confluent Hub client
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-s3:10.5.0

# Install AWS SDK dependencies for S3 Sink Connector
USER root
RUN mkdir -p /usr/share/confluent-hub-components

USER appuser
