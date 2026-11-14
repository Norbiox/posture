# Posture

Posture lets one person control their IKEA Idasen desk over the local network, tracks how long they sit and stand, and moves the desk automatically during work hours.

## Language

### Desk

**Desk**:
The single IKEA Idasen desk that Posture controls.
_Avoid_: Table, device

**Height**:
The current height of the desktop in centimetres, exactly as the Desk reports it.
_Avoid_: Level, position

**Preset**:
A named, saved Height that the Desk moves to on request.
_Avoid_: Position, saved position, favourite

**Stance**:
Whether the Desk is Sitting or Standing, decided by comparing its Height with a single threshold. Every Height belongs to exactly one Stance.
_Avoid_: Posture, position, mode

### Time

**Work Hours**:
The daily time window on Workdays in which Automations run.
_Avoid_: Office hours, schedule

**Workday**:
A weekday on which Work Hours apply, unless it is a Holiday.
_Avoid_: Business day

**Holiday**:
A date on which Work Hours do not apply, even if it falls on a Workday.
_Avoid_: Day off, vacation

### Automation

**Automation**:
A user-defined rule that moves the Desk to a Preset without a click. It is either a Schedule or a Timer.
_Avoid_: Trigger, job, scenario

**Schedule**:
An Automation that moves the Desk to a Preset at a fixed time of day.
_Avoid_: Cron, alarm

**Timer**:
An Automation that moves the Desk to a Preset after the Desk has stayed in one Stance without a break for a set number of minutes.
_Avoid_: Reminder, countdown, rule

**Pause**:
A state in which no Automation moves the Desk until the end of the current day.
_Avoid_: Snooze, mute, disable
