from __future__ import annotations

import logging
import os

import pytest

from watchdog.utils import platform

if not platform.is_linux():
    pytest.skip("GNU/Linux only.", allow_module_level=True)

from watchdog.observers.api import EventQueue, ObservedWatch
from watchdog.observers.inotify import InotifyEmitter
from watchdog.observers.inotify_c import InotifyConstants, InotifyEvent
from watchdog.observers.inotify_move_event_grouper import PathedInotifyEvent


def test_queue_events_on_stopped_emitter_does_not_log_error(tmp_path, caplog):
    # on_thread_stop() clears the watch group when unschedule() stops the emitter
    # from another thread, so a cleared group is a normal shutdown, not a fault.
    emitter = InotifyEmitter(EventQueue(), ObservedWatch(tmp_path, recursive=False))
    with caplog.at_level(logging.DEBUG, logger="watchdog"):
        emitter.queue_events(emitter.timeout)
    assert not caplog.records


def test_event_read_while_emitter_stops_is_dropped_without_error(tmp_path, caplog):
    event_queue = EventQueue()
    emitter = InotifyEmitter(event_queue, ObservedWatch(tmp_path, recursive=False))

    class WatchGroupStoppedDuringRead:
        def read_event(self):
            # Simulate unschedule() stopping the emitter while read_event() returns an event.
            emitter._inotify = None  # noqa: SLF001
            event = InotifyEvent(1, InotifyConstants.IN_CREATE, 0, b"file")
            return PathedInotifyEvent(event, os.fsencode(tmp_path / "file"))

    emitter._inotify = WatchGroupStoppedDuringRead()  # noqa: SLF001
    with caplog.at_level(logging.DEBUG, logger="watchdog"):
        emitter.queue_events(emitter.timeout)
    assert not caplog.records
    assert event_queue.empty()
