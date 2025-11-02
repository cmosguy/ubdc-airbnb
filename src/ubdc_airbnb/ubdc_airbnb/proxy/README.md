# Proxy Service Abstraction

This module provides an abstraction layer for supporting multiple proxy service providers in the UBDC Airbnb project.

## Overview

The proxy service abstraction allows the application to work with different proxy providers without changing the core application code. This makes it easy to switch between providers or add new ones.

## Supported Providers

### Zyte Smart Proxy Manager

Zyte (formerly Scrapinghub/Crawlera) provides smart proxy services that automatically rotate IPs and handle bans.

**Configuration:**
```bash
export PROXY_PROVIDER=zyte
export ZYTE_API_KEY=your-zyte-api-key
```

**Features:**
- Automatic IP rotation
- Smart ban handling
- Requires custom CA certificate (automatically handled in Docker)

### Oxylabs Residential Proxies

Oxylabs provides residential and datacenter proxy services.

**Configuration:**
```bash
export PROXY_PROVIDER=oxylabs
export OXYLABS_USERNAME=your-username
export OXYLABS_PASSWORD=your-password
```

**Features:**
- Residential proxy network
- Session persistence options
- No custom CA certificate required

## Architecture

### Base Class: `ProxyService`

All proxy providers implement the `ProxyService` abstract base class, which defines:

- `get_proxy_url()`: Returns the proxy URL for use with requests
- `get_ca_certificate_url()`: Returns URL for CA certificate (if needed)
- `get_extra_headers()`: Returns any provider-specific HTTP headers
- `is_configured()`: Checks if the service is properly configured

### Factory Pattern

The `get_proxy_service()` factory function creates the appropriate proxy service instance based on the provider name:

```python
from ubdc_airbnb.proxy import get_proxy_service

# Create Zyte proxy service
proxy = get_proxy_service('zyte', api_key='your-key')

# Create Oxylabs proxy service
proxy = get_proxy_service('oxylabs', username='user', password='pass')

# Get proxy URL for use with requests
proxy_url = proxy.get_proxy_url()
```

## Usage

The proxy service is automatically configured in `settings.py` based on environment variables. The application code uses the `AIRBNB_PROXY` setting, which is set to the appropriate proxy URL.

### In Application Code

```python
from django.conf import settings
from ubdc_airbnb.airbnb_interface.airbnb_api import AirbnbApi

# The proxy is automatically applied
airbnb_client = AirbnbApi(proxy=settings.AIRBNB_PROXY)
```

## Adding a New Provider

To add support for a new proxy provider:

1. Create a new class in the `proxy` module that inherits from `ProxyService`
2. Implement all abstract methods
3. Add the provider to the factory function in `factory.py`
4. Update the documentation

Example:

```python
# proxy/newprovider.py
from ubdc_airbnb.proxy.base import ProxyService

class NewProviderProxyService(ProxyService):
    def __init__(self, api_key=None, **kwargs):
        super().__init__(api_key, **kwargs)
        # Provider-specific initialization

    def get_proxy_url(self):
        # Return proxy URL
        return f"http://{self.api_key}@proxy.example.com:8080"

    def get_ca_certificate_url(self):
        # Return CA cert URL or None
        return None
```

Then update `factory.py`:

```python
def get_proxy_service(provider, **kwargs):
    # ... existing code ...
    elif provider == "newprovider":
        return NewProviderProxyService(**kwargs)
```

## Environment Variables

| Variable | Description | Required For |
|----------|-------------|--------------|
| `PROXY_PROVIDER` | Proxy provider name (`zyte` or `oxylabs`) | All |
| `ZYTE_API_KEY` | Zyte API key | Zyte |
| `OXYLABS_USERNAME` | Oxylabs username | Oxylabs |
| `OXYLABS_PASSWORD` | Oxylabs password | Oxylabs |

## Docker Support

The Dockerfile has been updated to conditionally install CA certificates based on the `PROXY_PROVIDER` build argument:

```bash
# Build with Zyte (default)
docker build --build-arg PROXY_PROVIDER=zyte .

# Build with Oxylabs
docker build --build-arg PROXY_PROVIDER=oxylabs .
```

## Testing

To test a proxy configuration:

```python
from ubdc_airbnb.proxy import get_proxy_service

# Create and test proxy service
proxy = get_proxy_service('oxylabs', username='test', password='test')
print(f"Configured: {proxy.is_configured()}")
print(f"Proxy URL: {proxy.get_proxy_url()}")
print(f"CA Cert: {proxy.get_ca_certificate_url()}")
```
