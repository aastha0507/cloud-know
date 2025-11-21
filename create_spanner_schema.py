#!/usr/bin/env python3
"""Script to create Spanner schema manually."""
from google.cloud import spanner
from api.config.settings import settings

def create_schema():
    """Create Spanner database schema."""
    client = spanner.Client(project=settings.spanner_project_id)
    instance = client.instance(settings.spanner_instance_id)
    database = instance.database(settings.spanner_database_id)
    
    ddl_statements = [
        """CREATE TABLE document_metadata (
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
        )""",
        """CREATE TABLE document_relationships (
            relationship_id STRING(255) NOT NULL,
            source_document_id STRING(255) NOT NULL,
            target_document_id STRING(255) NOT NULL,
            relationship_type STRING(100) NOT NULL,
            strength FLOAT64,
            created_at TIMESTAMP NOT NULL,
            metadata_json JSON,
            PRIMARY KEY (relationship_id)
        )""",
        """CREATE TABLE conversation_metadata (
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
        )""",
        """CREATE INDEX idx_source ON document_metadata (source, source_id)""",
        """CREATE INDEX idx_relationships_source ON document_relationships (source_document_id)""",
        """CREATE INDEX idx_relationships_target ON document_relationships (target_document_id)""",
        """CREATE INDEX idx_conversations_platform ON conversation_metadata (platform, channel_id)"""
    ]
    
    print(f"Creating schema in database {settings.spanner_database_id}...")
    print(f"Project: {settings.spanner_project_id}")
    print(f"Instance: {settings.spanner_instance_id}")
    
    try:
        operation = database.update_ddl(ddl_statements)
        operation.result(timeout=300)  # Wait up to 5 minutes
        print("✅ Schema created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

if __name__ == "__main__":
    create_schema()

