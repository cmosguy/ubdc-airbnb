"""Oxylabs proxy service implementation."""

from typing import Optional

from ubdc_airbnb.proxy.base import ProxyService


class OxylabsProxyService(ProxyService):
    """Oxylabs Residential Proxies service implementation.

    Oxylabs provides residential and datacenter proxy services.

    Documentation: https://developers.oxylabs.io/scraper-apis/getting-started
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Oxylabs proxy service.

        Args:
            api_key: Oxylabs API key (alternative to username/password)
            username: Oxylabs username
            password: Oxylabs password
            **kwargs: Additional configuration options
                - host: Proxy host (default: pr.oxylabs.io)
                - port: Proxy port (default: 7777)
                - session_type: Session type (default: None, can be 'sticky' for session persistence)
        """
        super().__init__(api_key, **kwargs)
        self.username = username or api_key
        self.password = password
        self.host = kwargs.get("host", "pr.oxylabs.io")
        self.port = kwargs.get("port", 7777)
        self.session_type = kwargs.get("session_type")

    def get_proxy_url(self) -> Optional[str]:
        """Get the Oxylabs proxy URL.

        Returns:
            Proxy URL in format: http://<username>:<password>@<host>:<port>
            Returns None if credentials are not configured
        """
        if not self.username or not self.password:
            return None

        # Build username with session type if specified
        username = self.username
        if self.session_type:
            username = f"{self.username}-session-{self.session_type}"

        return f"http://{username}:{self.password}@{self.host}:{self.port}"

    def get_ca_certificate_url(self) -> Optional[str]:
        """Get the URL for Oxylabs CA certificate.

        Oxylabs typically doesn't require a custom CA certificate.

        Returns:
            None (Oxylabs doesn't require custom CA certificates)
        """
        return None

    def is_configured(self) -> bool:
        """Check if the proxy service is properly configured.

        Returns:
            True if both username and password are set
        """
        return self.username is not None and self.password is not None

    def __repr__(self) -> str:
        """String representation of the proxy service."""
        return f"OxylabsProxyService(host={self.host}, port={self.port}, configured={self.is_configured()})"
