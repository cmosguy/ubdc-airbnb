"""Base class for proxy services."""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class ProxyService(ABC):
    """Abstract base class for proxy service implementations.

    This class defines the interface that all proxy service providers must implement.
    Different proxy providers (Zyte, Oxylabs, etc.) will have their own concrete implementations.
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize the proxy service.

        Args:
            api_key: API key for the proxy service
            **kwargs: Additional provider-specific configuration options
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    def get_proxy_url(self) -> Optional[str]:
        """Get the proxy URL to be used with requests.

        Returns:
            Proxy URL string in format suitable for requests library,
            or None if proxy is not configured
        """
        pass

    @abstractmethod
    def get_ca_certificate_url(self) -> Optional[str]:
        """Get the URL for the proxy provider's CA certificate.

        Some proxy providers require custom CA certificates to be installed.

        Returns:
            URL to the CA certificate file, or None if not required
        """
        pass

    def get_extra_headers(self) -> Dict[str, str]:
        """Get any extra HTTP headers required by this proxy provider.

        Returns:
            Dictionary of HTTP headers
        """
        return {}

    def is_configured(self) -> bool:
        """Check if the proxy service is properly configured.

        Returns:
            True if the service has the minimum required configuration
        """
        return self.api_key is not None
