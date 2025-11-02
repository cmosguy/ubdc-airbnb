"""Zyte (formerly Crawlera) proxy service implementation."""

from typing import Optional

from ubdc_airbnb.proxy.base import ProxyService


class ZyteProxyService(ProxyService):
    """Zyte Smart Proxy Manager service implementation.

    Zyte (formerly Scrapinghub/Crawlera) provides smart proxy services
    that automatically rotate IPs and handle bans.

    Documentation: https://docs.zyte.com/smart-proxy-manager.html
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize Zyte proxy service.

        Args:
            api_key: Zyte API key
            **kwargs: Additional configuration options
                - host: Proxy host (default: proxy.crawlera.com)
                - port: Proxy port (default: 8011)
        """
        super().__init__(api_key, **kwargs)
        self.host = kwargs.get("host", "proxy.crawlera.com")
        self.port = kwargs.get("port", 8011)

    def get_proxy_url(self) -> Optional[str]:
        """Get the Zyte proxy URL.

        Returns:
            Proxy URL in format: http://<api_key>:@<host>:<port>
            Returns None if API key is not configured
        """
        if not self.api_key:
            return None

        return f"http://{self.api_key}:@{self.host}:{self.port}"

    def get_ca_certificate_url(self) -> Optional[str]:
        """Get the URL for Zyte's CA certificate.

        Returns:
            URL to Zyte's Smart Proxy CA certificate
        """
        return "https://docs.zyte.com/_static/zyte-smartproxy-ca.crt"

    def __repr__(self) -> str:
        """String representation of the proxy service."""
        return f"ZyteProxyService(host={self.host}, port={self.port}, configured={self.is_configured()})"
