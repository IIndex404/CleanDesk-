"""Read the current Windows output-device peak without capturing microphone data."""

from __future__ import annotations

import sys
import time


class SystemAudioMeter:
    """Small, failure-tolerant wrapper around Windows IAudioMeterInformation."""

    def __init__(self, reconnect_interval: float = 2.0):
        self.reconnect_interval = reconnect_interval
        self.device_name = ""
        self.last_error = ""
        self._meter = None
        self._device = None
        self._comtypes = None
        self._com_initialized = False
        self._last_connect_attempt = 0.0

    @property
    def available(self) -> bool:
        return self._meter is not None

    def _connect(self) -> bool:
        if sys.platform != "win32":
            self.last_error = "系统音频频谱仅支持 Windows"
            return False

        now = time.monotonic()
        if now - self._last_connect_attempt < self.reconnect_interval:
            return False
        self._last_connect_attempt = now

        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

            if not self._com_initialized:
                comtypes.CoInitialize()
                self._com_initialized = True
                self._comtypes = comtypes

            device = AudioUtilities.GetSpeakers()
            interface = device._dev.Activate(
                IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None
            )
            self._meter = interface.QueryInterface(IAudioMeterInformation)
            self._device = device
            self.device_name = device.FriendlyName or "Windows 默认输出设备"
            self.last_error = ""
            return True
        except Exception as exc:
            self._meter = None
            self._device = None
            self.last_error = str(exc)
            return False

    def read_peak(self) -> float | None:
        """Return the latest normalized output peak, or None while unavailable."""
        if self._meter is None and not self._connect():
            return None
        try:
            return max(0.0, min(1.0, float(self._meter.GetPeakValue())))
        except Exception as exc:
            # The default endpoint can disappear when headphones/Bluetooth
            # devices change. Drop the stale COM object and retry later.
            self.last_error = str(exc)
            self._meter = None
            self._device = None
            self._last_connect_attempt = 0.0
            return None

    def close(self) -> None:
        self._meter = None
        self._device = None
        if self._com_initialized and self._comtypes is not None:
            try:
                self._comtypes.CoUninitialize()
            except Exception:
                pass
        self._com_initialized = False
        self._comtypes = None
