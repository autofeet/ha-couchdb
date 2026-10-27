## 3.5.3-2

- Add the upstream CouchDB icon to the HA store and app list.
- Open Fauxton in the HA sidebar through an authenticated ingress endpoint.
- Keep the management proxy private to the Supervisor; the 5984 API still requires CouchDB credentials.

## 3.5.3-1

- Initial HA OS wrapper around the official CouchDB 3.5.3 image.
- Persistent databases and runtime configuration in HA app data.
- Authenticated access and Obsidian LiveSync CORS defaults.
- Reviewed upstream update proposals and container CI.
