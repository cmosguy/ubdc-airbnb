"""Proxy service abstraction layer for supporting multiple proxy providers."""

from ubdc_airbnb.proxy.base import ProxyService
from ubdc_airbnb.proxy.factory import get_proxy_service
from ubdc_airbnb.proxy.oxylabs import OxylabsProxyService
from ubdc_airbnb.proxy.zyte import ZyteProxyService

__all__ = [
    "ProxyService",
    "ZyteProxyService",
    "OxylabsProxyService",
    "get_proxy_service",
]
