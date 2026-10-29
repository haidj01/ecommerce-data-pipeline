#!/bin/bash

# Load environment variables from .env file
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please copy .env.example to .env and fill in your AWS credentials."
    exit 1
fi

source .env

# Wait for Kafka Connect to be ready
echo "Waiting for Kafka Connect to be ready..."
until curl -s http://localhost:8083/ > /dev/null; do
    echo "Kafka Connect is not ready yet. Retrying in 5 seconds..."
    sleep 5
done
echo "Kafka Connect is ready!"

# Function to create connector with environment variable substitution
create_connector() {
    local connector_file=$1
    local connector_name=$(basename "$connector_file" .json)

    echo "Creating connector: $connector_name"

    # Read the connector config and substitute environment variables
    config=$(cat "$connector_file" | \
        sed "s/\${env:AWS_DEFAULT_REGION}/$AWS_DEFAULT_REGION/g" | \
        sed "s/\${env:S3_BUCKET_NAME}/$S3_BUCKET_NAME/g")

    # Create the connector
    response=$(curl -s -X POST http://localhost:8083/connectors \
        -H "Content-Type: application/json" \
        -d "$config")

    # Check if successful
    if echo "$response" | grep -q "error_code"; then
        echo "Failed to create connector $connector_name:"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        echo "Successfully created connector: $connector_name"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    fi
    echo ""
}

# Create all connectors
for connector_file in connectors/*.json; do
    create_connector "$connector_file"
done

echo "Done!"
