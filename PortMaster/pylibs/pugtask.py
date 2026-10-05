# SPDX-License-Identifier: MIT
#
# Threading helpers for the GUI.
#
# The rule: SDL, scenes and the template data (set_data) belong to the main
# thread. Slow work (downloads, installs, scans) runs on worker threads and
# talks back to the main thread through a MainThreadDispatcher.
#
# Nothing in here imports SDL so it can be tested on its own.

import queue
import threading
import time

from loguru import logger


def on_main_thread():
    return threading.current_thread() is threading.main_thread()


class _Call:
    __slots__ = ('fn', 'args', 'kwargs', 'done', 'result', 'error')

    def __init__(self, fn, args, kwargs, wait):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.done = threading.Event() if wait else None
        self.result = None
        self.error = None


class MainThreadDispatcher:
    """
    A queue of functions to run on the main thread.

    Workers use post() for fire and forget updates, and call() when they need
    an answer (eg: a message box). The main thread runs drain() once a frame.
    """

    def __init__(self):
        self._queue = queue.Queue()

    def post(self, fn, *args, **kwargs):
        if on_main_thread():
            fn(*args, **kwargs)
            return

        self._queue.put(_Call(fn, args, kwargs, False))

    def call(self, fn, *args, **kwargs):
        """
        Run fn on the main thread and return its result, re-raising any
        exception in the calling thread.
        """
        if on_main_thread():
            return fn(*args, **kwargs)

        item = _Call(fn, args, kwargs, True)
        self._queue.put(item)
        item.done.wait()

        if item.error is not None:
            raise item.error

        return item.result

    def drain(self, max_items=None):
        """
        Run queued functions, returns how many ran.
        """
        count = 0
        while max_items is None or count < max_items:
            try:
                item = self._queue.get_nowait()

            except queue.Empty:
                break

            count += 1
            try:
                item.result = item.fn(*item.args, **item.kwargs)

            except BaseException as err:
                if item.done is None:
                    logger.exception(f"Error in posted call {item.fn!r}")
                else:
                    item.error = err

            finally:
                if item.done is not None:
                    item.done.set()

        return count

    def pending(self):
        return not self._queue.empty()


class Task:
    """
    Runs one function on a worker thread.
    """

    def __init__(self, fn, *args, name=None, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.error = None
        self.cancel_requested = threading.Event()
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, name=name or f"task-{getattr(fn, '__name__', 'fn')}", daemon=True)

    def _run(self):
        try:
            self.result = self.fn(*self.args, **self.kwargs)

        except BaseException as err:
            self.error = err

        finally:
            self.done.set()

    def start(self):
        self.thread.start()
        return self

    def cancel(self):
        self.cancel_requested.set()

    def is_worker(self):
        return threading.current_thread() is self.thread

    def get(self):
        """
        Result of the task, re-raising its exception. Only call once done.
        """
        if self.error is not None:
            raise self.error

        return self.result


class FrameStats:
    """
    Opt-in frame timing (PM_PERF=1).

    The interesting number is the gap between frames: work done between two
    frames (eg: unzipping between progress callbacks) shows up there even when
    each frame on its own is quick.
    """

    SLOW_GAP = 0.050

    def __init__(self, enabled, clock=time.perf_counter, log=None):
        self.enabled = enabled
        self.clock = clock
        self.log = log or logger.info
        self.last_frame = None
        self.window_start = None
        self.frames = 0
        self.worst_gap = 0.0
        self.slow_frames = 0

    def frame(self, context=""):
        if not self.enabled:
            return

        now = self.clock()

        if self.last_frame is not None:
            gap = now - self.last_frame
            self.worst_gap = max(self.worst_gap, gap)

            if gap > self.SLOW_GAP:
                self.slow_frames += 1
                self.log(f"PERF slow frame: {gap * 1000:.0f} ms [{context}]")

        else:
            self.window_start = now

        self.last_frame = now
        self.frames += 1

        if now - self.window_start >= 1.0:
            self.log(
                f"PERF {self.frames / (now - self.window_start):.1f} fps, "
                f"worst gap {self.worst_gap * 1000:.0f} ms, "
                f"slow frames {self.slow_frames} [{context}]")

            self.window_start = now
            self.frames = 0
            self.worst_gap = 0.0
            self.slow_frames = 0


__all__ = (
    'FrameStats',
    'MainThreadDispatcher',
    'Task',
    'on_main_thread',
    )
