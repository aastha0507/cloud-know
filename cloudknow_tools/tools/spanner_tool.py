"""MCP Tool for Google Cloud Spanner Metadata Database operations."""
from typing import List, Dict, Any, Optional
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types
from api.config.settings import settings
import json
from datetime import datetime


class SpannerTool:
    """MCP Tool for interacting with Google Cloud Spanner Metadata Database."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        database_id: Optional[str] = None
    ):
        """Initialize Spanner tool.
        
        Args:
            project_id: GCP project ID. If None, uses settings.
            instance_id: Spanner instance ID. If None, uses settings.
            database_id: Spanner database ID. If None, uses settings.
        """
        import os
        from google.auth import default
        
        # Ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid file if set
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and not os.path.exists(creds_path):
            # If the path doesn't exist, unset it to use default credentials
            # This handles placeholder values like "path/to/service-account.json"
            if "path/to" in creds_path or not os.path.isfile(creds_path):
                os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        
        self.project_id = project_id or settings.spanner_project_id
        self.instance_id = instance_id or settings.spanner_instance_id
        self.database_id = database_id or settings.spanner_database_id
        
        self.client = spanner.Client(project=self.project_id)
        self.instance = self.client.instance(self.instance_id)
        self.database = self.instance.database(self.database_id)
        
        # Ensure tables exist
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure required database schema exists."""
        try:
            # Check if tables exist by trying to query them
            with self.database.snapshot() as snapshot:
                snapshot.execute_sql("SELECT COUNT(*) FROM document_metadata LIMIT 1")
            # Tables exist, no need to create
            return
        except Exception as e:
            # Tables don't exist, create them
            error_msg = str(e).lower()
            if "table not found" in error_msg or "not found" in error_msg:
                try:
                    self._create_schema()
                except Exception as create_error:
                    # Log but don't fail - schema might be created by another process
                    print(f"Warning: Could not create schema automatically: {create_error}")
                    print("You may need to create the schema manually. See SPANNER_SCHEMA.md")
            else:
                # Different error, might be permission issue
                print(f"Warning: Could not verify schema: {e}")
    
    def _create_schema(self):
        """Create database schema for metadata storage."""
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
        
        print("Creating Spanner schema...")
        operation = self.database.update_ddl(ddl_statements)
        operation.result(timeout=300)  # Wait up to 5 minutes for operation to complete
        print("Spanner schema created successfully!")
    
    def store_document_metadata(
        self,
        document_id: str,
        source: str,
        source_id: str,
        title: Optional[str] = None,
        content_type: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store document metadata in Spanner.
        
        Args:
            document_id: Unique document identifier
            source: Source platform (e.g., "google_drive", "jira")
            source_id: ID in the source platform
            title: Document title
            content_type: MIME type or content type
            file_path: File path or URL
            file_size: File size in bytes
            owner: Document owner
            tags: List of tags
            metadata: Additional metadata dictionary
            
        Returns:
            True if successful
        """
        try:
            now = datetime.utcnow()
            
            # Check if document already exists to preserve created_at
            created_at = now
            try:
                with self.database.snapshot() as snapshot:
                    result = snapshot.read(
                        "document_metadata",
                        columns=["created_at"],
                        keyset=spanner.KeySet(keys=[(document_id,)])
                    )
                    for row in result:
                        created_at = row[0]  # Preserve existing created_at
                        break
            except Exception:
                # Document doesn't exist, use current time
                created_at = now
            
            def upsert_metadata(transaction):
                # Use insert_or_update to handle duplicates gracefully
                transaction.insert_or_update(
                    "document_metadata",
                    columns=[
                        "document_id", "source", "source_id", "title",
                        "content_type", "file_path", "file_size",
                        "created_at", "updated_at", "owner", "tags", "metadata_json"
                    ],
                    values=[(
                        document_id,
                        source,
                        source_id,
                        title,
                        content_type,
                        file_path,
                        file_size,
                        created_at,  # Preserve original created_at if exists
                        now,  # Always update updated_at
                        owner,
                        tags or [],
                        json.dumps(metadata or {})
                    )]
                )
            
            self.database.run_in_transaction(upsert_metadata)
            return True
        except Exception as e:
            raise Exception(f"Error storing document metadata: {str(e)}")
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Metadata dictionary or None if not found
        """
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                "SELECT * FROM document_metadata WHERE document_id = @document_id",
                params={"document_id": document_id},
                param_types={"document_id": param_types.STRING}
            )
            
            row = results.one_or_none()
            if row:
                return {
                    "document_id": row[0],
                    "source": row[1],
                    "source_id": row[2],
                    "title": row[3],
                    "content_type": row[4],
                    "file_path": row[5],
                    "file_size": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "owner": row[9],
                    "tags": list(row[10]) if row[10] else [],
                    "metadata": json.loads(row[11]) if row[11] else {}
                }
            return None
    
    def create_relationship(
        self,
        relationship_id: str,
        source_document_id: str,
        target_document_id: str,
        relationship_type: str,
        strength: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a relationship between two documents.
        
        Args:
            relationship_id: Unique relationship identifier
            source_document_id: Source document ID
            target_document_id: Target document ID
            relationship_type: Type of relationship (e.g., "references", "related", "version_of")
            strength: Relationship strength (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            now = datetime.utcnow()
            
            def insert_relationship(transaction):
                transaction.insert(
                    "document_relationships",
                    columns=[
                        "relationship_id", "source_document_id", "target_document_id",
                        "relationship_type", "strength", "created_at", "metadata_json"
                    ],
                    values=[(
                        relationship_id,
                        source_document_id,
                        target_document_id,
                        relationship_type,
                        strength,
                        now,
                        json.dumps(metadata or {})
                    )]
                )
            
            self.database.run_in_transaction(insert_relationship)
            return True
        except Exception as e:
            raise Exception(f"Error creating relationship: {str(e)}")
    
    def get_document_relationships(
        self,
        document_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all relationships for a document.
        
        Args:
            document_id: Document ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of relationship dictionaries
        """
        with self.database.snapshot() as snapshot:
            query = """
                SELECT * FROM document_relationships
                WHERE source_document_id = @doc_id OR target_document_id = @doc_id
            """
            params = {"doc_id": document_id}
            param_types_dict = {"doc_id": param_types.STRING}
            
            if relationship_type:
                query += " AND relationship_type = @rel_type"
                params["rel_type"] = relationship_type
                param_types_dict["rel_type"] = param_types.STRING
            
            results = snapshot.execute_sql(query, params=params, param_types=param_types_dict)
            
            relationships = []
            for row in results:
                relationships.append({
                    "relationship_id": row[0],
                    "source_document_id": row[1],
                    "target_document_id": row[2],
                    "relationship_type": row[3],
                    "strength": row[4],
                    "created_at": row[5],
                    "metadata": json.loads(row[6]) if row[6] else {}
                })
            
            return relationships
    
    def search_metadata(
        self,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search document metadata by various criteria.
        
        Args:
            source: Filter by source platform
            tags: Filter by tags (documents must have all tags)
            owner: Filter by owner
            
        Returns:
            List of matching document metadata
        """
        with self.database.snapshot() as snapshot:
            conditions = []
            params = {}
            param_types_dict = {}
            
            if source:
                conditions.append("source = @source")
                params["source"] = source
                param_types_dict["source"] = param_types.STRING
            
            if owner:
                conditions.append("owner = @owner")
                params["owner"] = owner
                param_types_dict["owner"] = param_types.STRING
            
            if tags:
                for i, tag in enumerate(tags):
                    conditions.append(f"@tag_{i} IN UNNEST(tags)")
                    params[f"tag_{i}"] = tag
                    param_types_dict[f"tag_{i}"] = param_types.STRING
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT * FROM document_metadata WHERE {where_clause}"
            
            results = snapshot.execute_sql(query, params=params, param_types=param_types_dict)
            
            documents = []
            for row in results:
                documents.append({
                    "document_id": row[0],
                    "source": row[1],
                    "source_id": row[2],
                    "title": row[3],
                    "content_type": row[4],
                    "file_path": row[5],
                    "file_size": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "owner": row[9],
                    "tags": list(row[10]) if row[10] else [],
                    "metadata": json.loads(row[11]) if row[11] else {}
                })
            
            return documents

