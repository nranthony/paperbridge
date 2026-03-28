"""PaperBridge settings — publication-related env vars only."""

from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class PaperBridgeSettings(BaseSettings):
    """Configuration loaded from environment variables.

    Covers only publication-API keys and HTTP defaults.
    No auto-created directories, no global singleton.
    """

    ncbi_api_key: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("NCBI_API_KEY", "ncbi_api_key"),
    )
    unpaywall_email: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("MY_EMAIL", "my_email", "UNPAYWALL_EMAIL", "unpaywall_email"),
    )
    request_timeout: int = Field(30, validation_alias=AliasChoices("REQUEST_TIMEOUT", "request_timeout"))
    max_retries: int = Field(3, validation_alias=AliasChoices("MAX_RETRIES", "max_retries"))

    zotero_api_key: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("ZOTERO_API_KEY", "zotero_api_key"),
    )
    zotero_user_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("ZOTERO_USER_ID", "zotero_user_id"),
    )
    zotero_group_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("ZOTERO_GROUP_ID", "zotero_group_id"),
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}
