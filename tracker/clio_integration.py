"""Clio API integration helpers.

This module contains stubbed classes and functions for integrating the
time tracker with Clio, a cloud‑based practice management platform.  In
a production setting, these helpers would handle OAuth2 authentication
flows, fetch matters and contacts, and push time entries to Clio via
their REST API.  The current implementation provides scaffolding for
future development and does not perform any network requests.
"""
from __future__ import annotations

from typing import List, Dict, Optional


class ClioClient:
    """Placeholder client for interacting with the Clio API."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        # In a full implementation, access_token would be obtained via OAuth2
        self.access_token = access_token

    def authenticate(self) -> None:
        """
        Perform the OAuth2 authentication flow to obtain an access token.

        This method is left unimplemented; refer to Clio's developer
        documentation for details on registering an app, obtaining a client
        ID/secret, and completing the OAuth2 authorisation code flow.
        """
        raise NotImplementedError("Clio OAuth2 authentication not implemented.")

    def list_matters(self) -> List[Dict[str, str]]:
        """
        Fetch a list of matters available to the authenticated user.

        :return: A list of dictionaries with at least ``id`` and ``name`` keys.
        """
        # A real implementation would call the `/matters` endpoint.
        return []

    def create_time_entry(
        self,
        matter_id: str,
        start_time: str,
        end_time: str,
        duration_sec: float,
        description: str,
    ) -> Dict[str, str]:
        """
        Create a time entry in Clio for the specified matter.

        :param matter_id: The identifier of the matter in Clio.
        :param start_time: ISO formatted start timestamp.
        :param end_time: ISO formatted end timestamp.
        :param duration_sec: Length of the time entry in seconds.
        :param description: Description of work performed.
        :return: A dictionary representing the newly created time entry.
        """
        # A real implementation would POST to `/activities` or `/time_entries`.
        return {
            "id": "mock-id",
            "matter_id": matter_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_sec": str(duration_sec),
            "description": description,
        }
