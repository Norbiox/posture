# Posture holds a persistent BLE connection to the Desk

Posture keeps one permanent BLE connection to the Desk, listens to its height notifications, and reconnects automatically when the link drops. All other clients (the web UI, the dmenu script on laptops) control the Desk only through Posture's HTTP API, never over BLE directly. We chose this over polling the Height every 5 minutes because, once every client goes through Posture, nothing else needs the Desk's single BLE slot, and a persistent link gives exact Sitting/Standing statistics, accurate Timers, and live Height for the UI.

## Considered Options

- **Poll every 5 minutes, connect on demand**: leaves the BLE slot free for other clients, but statistics and Timers are off by up to 5 minutes and moves made with the Desk's physical buttons are seen late.

## Consequences

- The IKEA/Linak phone app cannot connect while Posture runs.
- The VM running Posture needs the Bluetooth adapter passed through via USB.
