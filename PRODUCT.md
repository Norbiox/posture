# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One person: the owner of one IKEA Idasen desk. They keep Posture open in a desktop browser tab
next to their work. The UI must also work on a phone. Nobody else sees the interface.

## Product Purpose

Posture moves the Desk automatically during Work Hours and tracks how long the owner sits and
stands. It runs in the background. The owner opens the UI rarely: to check the current state,
to move the Desk by hand, to pause Automations, or to change configuration.

Success: the owner forgets the Desk most of the day, and the UI answers "what is the Desk doing
and what happens next" at a glance.

## Positioning

A self-hosted replacement for the IKEA/Linak phone app. It keeps a permanent BLE Connection and
runs Automations (Schedules and Timers) without the owner. The phone app cannot do that.

## Operating Context

- Runs on an Alpine VM in a trusted LAN. No authentication.
- Live state comes over a WebSocket: Height, Stance, Connection, paused state.
- Manual movement is hold-to-move: the Desk moves only while the button is pressed.
- Tabs today: Control, Stats, Automations, Settings, Logs.

## Capabilities and Constraints

- Terms come from `GLOSSARY.md`: Desk, Height, Preset, Stance, Stance Period, Connection,
  Work Hours, Workday, Holiday, Automation, Schedule, Timer. The UI uses these words.
- Stack: Svelte 5, Tailwind 4, uPlot for charts. Built by Vite into `frontend/dist`.
- While the Connection is down, the last known Height stays in force.

## Evidence on Hand

Real data only from the running app or the fake Desk (`POSTURE_DESK_MAC=fake`).

## Product Principles

1. Background first: the default view tells state and the next Automation, not controls.
2. Safety is explicit: Stop and hold-to-move never hide or lag.
3. One owner, no explanation: dense and direct, no onboarding copy.
4. Glossary words only.
