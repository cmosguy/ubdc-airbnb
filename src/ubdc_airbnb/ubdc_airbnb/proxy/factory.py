"""Factory for creating proxy service instances."""

from typing import Optional

from ubdc_airbnb.proxy.base import ProxyService
from ubdc_airbnb.proxy.oxylabs import OxylabsProxyService
from ubdc_airbnb.proxy.zyte import ZyteProxyService


def get_proxy_service(
    provider: str,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs,
) -> ProxyService:
    """Factory function to create the appropriate proxy service instance.

    Args:
        provider: Name of the proxy provider ('zyte' or 'oxylabs')
        api_key: API key for the proxy service
        username: Username for proxy authentication (primarily for Oxylabs)
        password: Password for proxy authentication (primarily for Oxylabs)
        **kwargs: Additional provider-specific configuration options

    Returns:
        Configured ProxyService instance

    Raises:
        ValueError: If provider is not supported

    Examples:
        >>> # Create Zyte proxy service
        >>> proxy = get_proxy_service('zyte', api_key='your-zyte-key')

        >>> # Create Oxylabs proxy service with username/password
        >>> proxy = get_proxy_service('oxylabs', username='user', password='pass')

        >>> # Create Oxylabs proxy service with API key
        >>> proxy = get_proxy_service('oxylabs', api_key='your-oxylabs-key', password='pass')
    """
    provider = provider.lower().strip()

    if provider == "zyte":
        return ZyteProxyService(api_key=api_key, **kwargs)
    elif provider == "oxylabs":
        return OxylabsProxyService(
            api_key=api_key,
            username=username,
            password=password,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported proxy provider: {provider}. "
            f"Supported providers: 'zyte', 'oxylabs'"
        )
