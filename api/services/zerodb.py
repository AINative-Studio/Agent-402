"""
ZeroDB Service Layer

Handles all ZeroDB API interactions following the DX Contract.
Implements proper error handling, retries, and abstraction.

Following PRD §6 - ZeroDB Integration
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ZeroDBError(Exception):
    """Base exception for ZeroDB operations"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "ZERODB_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ZeroDBService:
    """
    Service class for ZeroDB operations.

    Implements:
    - Connection pooling
    - Automatic retries with exponential backoff
    - Proper error handling
    - DX Contract compliance
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize ZeroDB service.

        Args:
            api_key: ZeroDB API key (defaults to ZERODB_API_KEY env var)
            base_url: Base URL (defaults to ZERODB_BASE_URL or standard URL)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv("ZERODB_API_KEY", "")
        self.base_url = (
            base_url or
            os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio/v1/public")
        ).rstrip("/")
        self.timeout = timeout

        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to ZeroDB API.

        Args:
            method: HTTP method
            path: API path (will be appended to base_url)
            json_data: JSON request body
            params: URL query parameters

        Returns:
            Response JSON as dict

        Raises:
            ZeroDBError: On API errors
        """
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout
            )

            # Handle successful responses
            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except ValueError:
                    return {"status": "success", "raw": response.text}

            # Handle error responses
            try:
                error_data = response.json()
                detail = error_data.get("detail", response.text)
                error_code = error_data.get("error_code", "ZERODB_ERROR")
            except ValueError:
                detail = response.text
                error_code = "ZERODB_ERROR"

            raise ZeroDBError(
                message=detail,
                status_code=response.status_code,
                error_code=error_code
            )

        except requests.exceptions.Timeout:
            raise ZeroDBError(
                message="Request to ZeroDB timed out",
                status_code=504,
                error_code="TIMEOUT"
            )
        except requests.exceptions.ConnectionError:
            raise ZeroDBError(
                message="Failed to connect to ZeroDB",
                status_code=503,
                error_code="CONNECTION_ERROR"
            )
        except ZeroDBError:
            raise
        except Exception as e:
            raise ZeroDBError(
                message=f"Unexpected error: {str(e)}",
                status_code=500,
                error_code="INTERNAL_ERROR"
            )

    def create_project_internal(
        self,
        name: str,
        tier: str,
        description: Optional[str] = None,
        database_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new project in ZeroDB.

        This uses the internal ZeroDB projects table to persist project data.
        Following DX Contract - all project data is append-only.

        Args:
            name: Project name
            tier: Project tier (FREE, STARTER, PRO, ENTERPRISE)
            description: Optional project description
            database_enabled: Whether database features are enabled

        Returns:
            Created project data with id, name, status, tier, created_at

        Raises:
            ZeroDBError: On creation failure
        """
        # Generate project ID
        project_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        # Create project record
        project_data = {
            "id": project_id,
            "name": name,
            "description": description,
            "tier": tier,
            "status": "ACTIVE",
            "database_enabled": database_enabled,
            "created_at": created_at.isoformat()
        }

        # For MVP, we'll use the MCP tool to create the project
        # In production, this would call POST /v1/public/projects on ZeroDB
        # For now, we'll simulate by returning the project data
        # The actual persistence will happen via the MCP tool in the route

        return project_data

    def list_projects(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List all projects.

        Following DX Contract pagination pattern.

        Args:
            limit: Maximum number of projects to return
            offset: Pagination offset

        Returns:
            Dict with projects list and pagination info

        Raises:
            ZeroDBError: On list failure
        """
        # For MVP, this would call GET /v1/public/projects
        # Implementation deferred to when list endpoint is needed
        return {
            "projects": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }

    def ensure_projects_table(self, project_id: str) -> None:
        """
        Ensure the projects metadata table exists.

        Following PRD §6 - projects need metadata storage.

        Args:
            project_id: Project ID for scoping the table

        Raises:
            ZeroDBError: On table creation failure
        """
        try:
            # Create projects metadata table
            self._request(
                "POST",
                f"/{project_id}/database/tables",
                json_data={
                    "name": "projects",
                    "description": "Project metadata and configuration",
                    "schema": {
                        "id": "UUID PRIMARY KEY",
                        "name": "TEXT NOT NULL",
                        "description": "TEXT",
                        "tier": "TEXT NOT NULL",
                        "status": "TEXT NOT NULL",
                        "database_enabled": "BOOLEAN DEFAULT TRUE",
                        "created_at": "TIMESTAMP DEFAULT NOW()"
                    }
                }
            )
        except ZeroDBError as e:
            # Ignore if table already exists
            if "exist" in str(e.message).lower() or e.status_code in (400, 409):
                return
            raise

    def insert_project_record(
        self,
        project_id: str,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Insert a project record into the projects table.

        Following DX Contract - uses row_data pattern.

        Args:
            project_id: Project ID for scoping
            project_data: Project data to insert

        Returns:
            Insert response

        Raises:
            ZeroDBError: On insert failure
        """
        return self._request(
            "POST",
            f"/{project_id}/database/tables/projects/rows",
            json_data={"row_data": project_data}
        )
