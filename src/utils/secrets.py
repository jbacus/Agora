"""
Google Secret Manager integration for secure API key storage.

This module provides utilities to fetch secrets from Google Cloud Secret Manager.
Falls back to environment variables for local development.
"""
import os
from typing import Optional

from loguru import logger


def get_secret(secret_name: str, project_id: Optional[str] = None, version: str = "latest") -> Optional[str]:
    """
    Fetch a secret from Google Secret Manager or environment variables.

    Priority:
    1. Google Secret Manager (if running in GCP)
    2. Environment variable
    3. None (returns None if not found)

    Args:
        secret_name: Name of the secret
        project_id: GCP project ID (auto-detected if None)
        version: Secret version (default: "latest")

    Returns:
        Secret value as string, or None if not found

    Example:
        >>> api_key = get_secret("GEMINI_API_KEY")
        >>> if api_key:
        >>>     # Use the API key
    """
    # First, check environment variable (for local development)
    env_value = os.getenv(secret_name)
    if env_value:
        logger.debug(f"Secret '{secret_name}' loaded from environment variable")
        return env_value

    # Try to load from Google Secret Manager (for production)
    try:
        from google.cloud import secretmanager

        # Auto-detect project ID if not provided
        if not project_id:
            project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            logger.warning("GCP_PROJECT_ID not set, skipping Secret Manager lookup")
            return None

        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"

        # Access the secret
        try:
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Secret '{secret_name}' loaded from Google Secret Manager")
            return secret_value
        except Exception as e:
            logger.warning(f"Failed to fetch secret '{secret_name}' from Secret Manager: {e}")
            return None

    except ImportError:
        logger.debug("google-cloud-secret-manager not installed, using environment variables only")
        return None
    except Exception as e:
        logger.warning(f"Error accessing Secret Manager: {e}")
        return None


def get_secret_or_raise(secret_name: str, project_id: Optional[str] = None) -> str:
    """
    Fetch a secret from Google Secret Manager or environment variables.
    Raises an error if the secret is not found.

    Args:
        secret_name: Name of the secret
        project_id: GCP project ID (auto-detected if None)

    Returns:
        Secret value as string

    Raises:
        ValueError: If secret is not found
    """
    secret = get_secret(secret_name, project_id)
    if secret is None:
        raise ValueError(
            f"Secret '{secret_name}' not found. "
            f"Set it as an environment variable or in Google Secret Manager."
        )
    return secret


def set_secret(secret_name: str, secret_value: str, project_id: Optional[str] = None) -> bool:
    """
    Create or update a secret in Google Secret Manager.

    Args:
        secret_name: Name of the secret
        secret_value: Value to store
        project_id: GCP project ID (auto-detected if None)

    Returns:
        True if successful, False otherwise
    """
    try:
        from google.cloud import secretmanager
        from google.api_core import exceptions

        # Auto-detect project ID
        if not project_id:
            project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            logger.error("GCP_PROJECT_ID not set, cannot create secret")
            return False

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"

        # Try to create the secret (if it doesn't exist)
        try:
            secret = client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {
                        "replication": {"automatic": {}}
                    }
                }
            )
            logger.info(f"Created new secret: {secret_name}")
        except exceptions.AlreadyExists:
            logger.debug(f"Secret {secret_name} already exists, adding new version")
        except Exception as e:
            logger.error(f"Failed to create secret: {e}")
            return False

        # Add a new version with the secret value
        parent_secret = f"projects/{project_id}/secrets/{secret_name}"
        payload = secret_value.encode("UTF-8")

        try:
            version = client.add_secret_version(
                request={
                    "parent": parent_secret,
                    "payload": {"data": payload}
                }
            )
            logger.info(f"Added new version to secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add secret version: {e}")
            return False

    except ImportError:
        logger.error("google-cloud-secret-manager not installed")
        return False
    except Exception as e:
        logger.error(f"Error setting secret: {e}")
        return False


def list_secrets(project_id: Optional[str] = None) -> list:
    """
    List all secrets in Google Secret Manager for the project.

    Args:
        project_id: GCP project ID (auto-detected if None)

    Returns:
        List of secret names
    """
    try:
        from google.cloud import secretmanager

        if not project_id:
            project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            logger.error("GCP_PROJECT_ID not set")
            return []

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"

        secrets = []
        for secret in client.list_secrets(request={"parent": parent}):
            secret_name = secret.name.split("/")[-1]
            secrets.append(secret_name)

        return secrets

    except ImportError:
        logger.error("google-cloud-secret-manager not installed")
        return []
    except Exception as e:
        logger.error(f"Error listing secrets: {e}")
        return []
