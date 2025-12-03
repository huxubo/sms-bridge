# Recent Changes Overview

This project previously received several updates to make the web UI usable and improve reliability. The key changes are summarized below for quick reference.

## Added message polling endpoint
- Implemented a new `/_messages_json` HTTP route so the web front end can poll recent messages without hitting 404s.
- The endpoint returns SMS data in batches with configurable limits to avoid large payloads.

## Forwarding timeout safeguards
- Added configurable HTTP timeouts for outbound Telegram and PushPlus forwarding requests.
- Timeouts prevent long-running remote calls from blocking the SMS collection loop.

## Asynchronous forwarding
- Forwarding to Telegram and PushPlus is now dispatched through a thread pool, keeping SMS polling responsive.
- A `forwarder_workers` configuration option allows tuning concurrency based on deployment needs.
- Worker shutdown now waits for the forwarding executor to close cleanly, preventing orphaned threads.
- The forwarder automatically recreates its worker pool after a shutdown, so restarting the listener won't fail due to a closed thread pool.

## Optional HTTP Basic authentication
- All web routes (UI, polling endpoint, control actions) can be protected with HTTP Basic auth when `http.auth_user` and `http.auth_password` are set in the configuration.
- Browsers will prompt for credentials once and reuse them for subsequent API calls, adding a simple safeguard against unauthorized access when the service is exposed on a network.

## Status reporting endpoint
- Added a `/status` route so the web UI and API consumers can check whether the listener is running and when it last polled for messages.
- The page footer now updates automatically with the current run state and latest poll timestamp, helping confirm the service is active after restarts.
