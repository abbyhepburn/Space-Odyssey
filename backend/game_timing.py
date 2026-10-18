"""Authoritative timing shared with the renderer via flight snapshots (seconds)."""
ROUND_SECONDS = 15
COUNTDOWN_SECONDS = 3
WARNING_LEAD = 1.8
RESPONSE_WINDOW = .8
INPUT_GRACE = .2
TRACK_SPEED = 12.
BODY_MODES = frozenset(('SURFACE_RUN', 'RING_RACE', 'CRATER_LEAP', 'STORM_SHELTER'))
BODY_KINDS = frozenset(('HURDLE', 'GATE', 'PIT', 'RIDGE', 'STORM'))
BODY_ENCOUNTERS = (3.8, 7.2, 10.6, 14.0)

def encounter_times(mode, count):
    if mode in BODY_MODES:
        return list(BODY_ENCOUNTERS)
    if mode in ('SAMPLE_HUNT', 'BEACON_RELAY', 'RELAY_REPAIR', 'GRAVITY_SLING'):
        return [2.4 + i * 2.9 for i in range(count)]
    return [1.8 + (14.0 - 1.8) * i / max(1, count - 1) for i in range(count)]

def timing_snapshot():
    return dict(warning_lead_s=WARNING_LEAD, response_window_s=RESPONSE_WINDOW,
                input_grace_s=INPUT_GRACE, track_speed=TRACK_SPEED,
                countdown_s=COUNTDOWN_SECONDS)
