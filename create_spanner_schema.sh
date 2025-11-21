#!/bin/bash

# Create Spanner Schema
# This script creates the required tables in your Spanner database

PROJECT_ID="cloudknow-478811"
INSTANCE_ID="cloudknow-instance"
DATABASE_ID="cloudknow-db"

echo "Creating Spanner schema..."
echo "Project: $PROJECT_ID"
echo "Instance: $INSTANCE_ID"
echo "Database: $DATABASE_ID"
echo ""

# Create schema using gcloud
gcloud spanner databases ddl update $DATABASE_ID \
  --instance=$INSTANCE_ID \
  --ddl="
CREATE TABLE document_metadata (
    document_id STRING(255) NOT NULL,
    source STRING(100) NOT NULL,
    source_id STRING(255) NOT NULL,
    title STRING(500),
    content_type STRING(100),
    file_path STRING(1000),
    file_size INT64,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    owner STRING(255),
    tags ARRAY<STRING(100)>,
    metadata_json JSON,
    PRIMARY KEY (document_id)
);

CREATE TABLE document_relationships (
    relationship_id STRING(255) NOT NULL,
    source_document_id STRING(255) NOT NULL,
    target_document_id STRING(255) NOT NULL,
    relationship_type STRING(100) NOT NULL,
    strength FLOAT64,
    created_at TIMESTAMP NOT NULL,
    metadata_json JSON,
    PRIMARY KEY (relationship_id)
);

CREATE TABLE conversation_metadata (
    conversation_id STRING(255) NOT NULL,
    platform STRING(100) NOT NULL,
    channel_id STRING(255),
    thread_id STRING(255),
    title STRING(500),
    participants ARRAY<STRING(255)>,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    metadata_json JSON,
    PRIMARY KEY (conversation_id)
);

CREATE INDEX idx_source ON document_metadata (source, source_id);
CREATE INDEX idx_relationships_source ON document_relationships (source_document_id);
CREATE INDEX idx_relationships_target ON document_relationships (target_document_id);
CREATE INDEX idx_conversations_platform ON conversation_metadata (platform, channel_id);
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Schema created successfully!"
else
    echo ""
    echo "❌ Error creating schema. Please check your permissions and try again."
fi

