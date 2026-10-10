# Umbrel NAS Mount Monitor

A small, read-only HTTP health endpoint for a CIFS media mount on umbrelOS. `GET /health` returns `200 ok` only when the expected CIFS share is mounted at `/nas/Media` inside the container and the `Downloads`, `Movies`, and `TV Shows` directories respond to metadata checks on the same filesystem. Missing mounts, wrong sources, inaccessible directories, and stalled metadata calls return `503 unhealthy` within five seconds. The checker does not open media files, change mounts, or attempt recovery.

The Umbrel package binds one NAS parent directory at `/nas` with `read_only: true` and `rslave` propagation. The checker runs as user 1000 with a read-only container filesystem, no Linux capabilities, and no Docker socket. Only `/health` bypasses Umbrel proxy authentication, so an HTTP monitor such as Uptime Kuma can poll it. The endpoint returns no mount path or device details.

## Local configuration on Umbrel

Before installation, create these two plain-text files under `$UMBREL_ROOT/app-data/geniusnas-monitor/data/` **on Umbrel**:

- `nas-parent-path`: the absolute path to one NAS parent directly under `$UMBREL_ROOT/network/`.
- `expected-source`: the exact CIFS source for its `Media` share, in the form `//host/Media`.

Those values stay on the device and are read by `exports.sh` when Umbrel starts the app. The public app store contains no local hostname, IP address, mount path, credential, or notification setting. The source parent must already exist; Docker is configured not to create a missing host path.

Add this repository as an Umbrel Community App Store and install **NAS Mount Monitor**. Point an Uptime Kuma HTTP monitor at the app's `/health` URL. A 60-second interval and the desired notification can be configured in Kuma.

Run the checker tests with `python3 -m unittest discover -s geniusnas-monitor -v` from this repository root.
