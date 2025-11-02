# Proxy Service Migration Guide

## Overview

This project has been updated to support multiple proxy service providers through an abstraction layer. Previously, the project was hardcoded to use Zyte (Crawlera) as the proxy provider. Now you can easily switch between different providers or add new ones.

## What Changed

### Architecture

1. **New Proxy Module** (`ubdc_airbnb/proxy/`)
   - `base.py` - Abstract base class defining the proxy service interface
   - `zyte.py` - Zyte Smart Proxy Manager implementation
   - `oxylabs.py` - Oxylabs Residential Proxies implementation
   - `factory.py` - Factory function to create proxy service instances
   - `README.md` - Detailed documentation for the proxy module

2. **Updated Settings** (`core/settings.py`)
   - Removed hardcoded Zyte configuration
   - Added `PROXY_PROVIDER` environment variable
   - Added support for multiple providers with provider-specific configuration

3. **Updated Docker Configuration**
   - `Dockerfile` - Conditional CA certificate installation based on provider
   - `docker-compose.yml` - Added `PROXY_PROVIDER` build argument

4. **Updated Documentation**
   - `notes.md` - Added proxy configuration section
   - `README/setup.md` - Updated proxy setup instructions
   - `.env.example` - Added proxy configuration examples

## Migration Steps

### For Existing Zyte Users (No Action Required)

If you're already using Zyte and have `ZYTE_API_KEY` set, **everything will continue to work** as before. The system defaults to Zyte for backward compatibility.

Your existing `.env` file:
```bash
ZYTE_API_KEY=your-api-key
```

Continues to work without any changes!

### For New Oxylabs Users

To use Oxylabs instead of Zyte:

1. **Update your `.env` file:**
   ```bash
   PROXY_PROVIDER=oxylabs
   OXYLABS_USERNAME=your-username
   OXYLABS_PASSWORD=your-password
   ```

2. **Rebuild your Docker containers:**
   ```bash
   docker-compose build --build-arg PROXY_PROVIDER=oxylabs
   docker-compose up
   ```

3. **That's it!** The application will now use Oxylabs for all proxy requests.

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PROXY_PROVIDER` | Proxy provider name | `zyte` | No |
| `ZYTE_API_KEY` | Zyte API key | - | Yes (if using Zyte) |
| `OXYLABS_USERNAME` | Oxylabs username | - | Yes (if using Oxylabs) |
| `OXYLABS_PASSWORD` | Oxylabs password | - | Yes (if using Oxylabs) |

### Supported Providers

#### Zyte Smart Proxy Manager
- **Provider Name:** `zyte`
- **Configuration:** `ZYTE_API_KEY`
- **Features:**
  - Automatic IP rotation
  - Smart ban handling
  - Requires custom CA certificate (auto-installed)
- **Documentation:** https://docs.zyte.com/smart-proxy-manager.html

#### Oxylabs Residential Proxies
- **Provider Name:** `oxylabs`
- **Configuration:** `OXYLABS_USERNAME`, `OXYLABS_PASSWORD`
- **Features:**
  - Residential proxy network
  - Session persistence
  - No custom CA certificate required
- **Documentation:** https://developers.oxylabs.io/scraper-apis/getting-started

## Benefits of the New Architecture

1. **Flexibility** - Easy to switch between proxy providers without code changes
2. **Extensibility** - Simple to add new proxy providers
3. **Maintainability** - Clear separation of concerns
4. **Backward Compatibility** - Existing Zyte configurations continue to work
5. **Cost Optimization** - Choose the most cost-effective provider for your needs

## Adding a New Proxy Provider

If you want to add support for another proxy provider:

1. Create a new class in `ubdc_airbnb/proxy/` inheriting from `ProxyService`
2. Implement the required methods: `get_proxy_url()`, `get_ca_certificate_url()`
3. Add the provider to the factory in `factory.py`
4. Update documentation

See `ubdc_airbnb/proxy/README.md` for detailed instructions.

## Testing

Test your proxy configuration:

```python
from ubdc_airbnb.proxy import get_proxy_service

# Test Zyte
proxy = get_proxy_service('zyte', api_key='your-key')
print(proxy.get_proxy_url())

# Test Oxylabs
proxy = get_proxy_service('oxylabs', username='user', password='pass')
print(proxy.get_proxy_url())
```

## Troubleshooting

### "No proxy configured" warning
- Check that you've set the appropriate environment variables
- Verify `PROXY_PROVIDER` matches your configured provider
- Ensure credentials are correctly set in `.env` file

### CA Certificate errors (Zyte only)
- Rebuild Docker image to install Zyte CA certificate
- Use `docker-compose build --build-arg PROXY_PROVIDER=zyte`

### Proxy authentication errors
- Verify your API key/credentials are correct
- Check with your proxy provider's dashboard
- Ensure no extra whitespace in environment variables

## Support

For issues with:
- **Zyte:** https://www.zyte.com/support/
- **Oxylabs:** https://oxylabs.io/support/
- **This Implementation:** Open an issue in the project repository

## Technical Details

### Code Changes Summary

**No changes required in:**
- `managers.py` - Still uses `settings.AIRBNB_PROXY`
- `tasks.py` - Still uses `settings.AIRBNB_PROXY`
- `airbnb_api.py` - Still accepts proxy URL string

**Changes made in:**
- `settings.py` - Now dynamically constructs `AIRBNB_PROXY` using the factory
- `Dockerfile` - Conditional CA certificate installation
- `docker-compose.yml` - Added build arguments

This maintains backward compatibility while enabling new functionality!
