### Notes

### Proxy Configuration

This project supports multiple proxy providers:

#### Zyte Smart Proxy Manager (Default)
- API Reference: https://docs.zyte.com/smart-proxy-manager.html
- Configuration: Set `PROXY_PROVIDER=zyte` and `ZYTE_API_KEY=<your-key>`

#### Oxylabs Residential Proxies
- API Reference: https://developers.oxylabs.io/scraper-apis/getting-started
- Configuration: Set `PROXY_PROVIDER=oxylabs`, `OXYLABS_USERNAME=<your-username>`, and `OXYLABS_PASSWORD=<your-password>`

### Rules
listings-details: once-per-14-days
listing-calendars: once-per-day, starting at 8 o'clock
