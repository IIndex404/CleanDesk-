"""A calm, audio-reactive spectrum for the desktop header."""

from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCloseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.services.audio_meter import SystemAudioMeter


class MusicVisualizer(QWidget):
    """Smooth capsule spectrum driven by the Windows output peak meter."""

    BAR_COUNT = 72
    START_THRESHOLD = 0.03
    STOP_THRESHOLD = 0.012
    START_FRAMES = 7
    STOP_FRAMES = 20

    def __init__(self, parent=None, audio_meter=None):
        super().__init__(parent)
        self.setObjectName("musicVisualizer")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(480)
        self.setMaximumWidth(1100)
        self.setFixedHeight(92)

        self._phase = 0.0
        self._levels = [0.0] * self.BAR_COUNT
        self._targets = [0.0] * self.BAR_COUNT
        self._audio_level = 0.0
        self._activity_mix = 0.0
        self.last_peak = 0.0
        self.music_active = False
        self._start_counter = 0
        self._stop_counter = 0
        self._recent_peaks = deque(maxlen=8)
        self.audio_meter = audio_meter or SystemAudioMeter()

        self.animation_timer = QTimer(self)
        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation_timer.setInterval(36)
        self.animation_timer.timeout.connect(self._advance)
        self.animation_timer.start()

    def sizeHint(self) -> QSize:
        return QSize(930, 92)

    def minimumSizeHint(self) -> QSize:
        return QSize(480, 92)

    def _update_music_gate(self, raw_peak: float, average_peak: float) -> None:
        if self.music_active:
            if average_peak <= self.STOP_THRESHOLD:
                self._stop_counter += 1
            else:
                self._stop_counter = 0
            if self._stop_counter >= self.STOP_FRAMES:
                self.music_active = False
                self._start_counter = 0
        else:
            if raw_peak >= self.START_THRESHOLD:
                self._start_counter += 1
            else:
                self._start_counter = max(0, self._start_counter - 2)
            if self._start_counter >= self.START_FRAMES:
                self.music_active = True
                self._stop_counter = 0

    def _advance(self) -> None:
        peak = self.audio_meter.read_peak()
        raw_peak = 0.0 if peak is None else max(0.0, min(1.0, peak))
        self.last_peak = raw_peak
        self._recent_peaks.append(raw_peak)
        average_peak = sum(self._recent_peaks) / len(self._recent_peaks)
        self._update_music_gate(raw_peak, average_peak)

        effective_peak = average_peak if self.music_active else 0.0
        mapped_peak = min(1.0, math.sqrt(effective_peak) * 0.9)
        energy_speed = 0.32 if mapped_peak > self._audio_level else 0.09
        self._audio_level += (mapped_peak - self._audio_level) * energy_speed

        activity_target = 1.0 if self.music_active else 0.0
        activity_speed = 0.075 if activity_target > self._activity_mix else 0.045
        self._activity_mix += (activity_target - self._activity_mix) * activity_speed
        self._phase += 0.038 + self._audio_level * 0.085

        for index in range(self.BAR_COUNT):
            position = index / max(1, self.BAR_COUNT - 1)
            distance = abs(position - 0.5) * 2.0
            envelope = 0.48 + 0.52 * (1.0 - distance ** 1.65)
            wave_a = 0.5 + 0.5 * math.sin(self._phase * 2.0 + index * 0.34)
            wave_b = 0.5 + 0.5 * math.sin(self._phase * 1.13 - index * 0.17 + 1.2)
            wave_c = 0.5 + 0.5 * math.sin(self._phase * 3.35 + index * 0.09)
            shape = 0.28 + 0.42 * wave_a + 0.21 * wave_b + 0.09 * wave_c
            self._targets[index] = min(
                1.0,
                self._audio_level * envelope * shape * self._activity_mix,
            )

        for index, target in enumerate(self._targets):
            speed = 0.31 if target > self._levels[index] else 0.14
            self._levels[index] += (target - self._levels[index]) * speed
        self.update()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.animation_timer.stop()
        self.audio_meter.close()
        super().closeEvent(event)

    @staticmethod
    def _mix_color(left: QColor, right: QColor, amount: float) -> QColor:
        amount = max(0.0, min(1.0, amount))
        return QColor(
            round(left.red() + (right.red() - left.red()) * amount),
            round(left.green() + (right.green() - left.green()) * amount),
            round(left.blue() + (right.blue() - left.blue()) * amount),
        )

    @classmethod
    def _bar_color(cls, position: float) -> QColor:
        cyan = QColor(136, 231, 255)
        lilac = QColor(203, 190, 255)
        warm = QColor(255, 226, 111)
        if position <= 0.58:
            return cls._mix_color(cyan, lilac, position / 0.58)
        return cls._mix_color(lilac, warm, (position - 0.58) / 0.42)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        panel = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setPen(QPen(QColor(255, 255, 255, 34), 1.0))
        painter.setBrush(QColor(8, 13, 27, 72))
        painter.drawRoundedRect(panel, 25.0, 25.0)

        left_padding = 27.0
        right_padding = 27.0
        usable_width = max(1.0, self.width() - left_padding - right_padding)
        step = usable_width / self.BAR_COUNT
        bar_width = max(3.2, min(6.4, step * 0.58))
        centre_y = self.height() / 2.0

        painter.setPen(QPen(QColor(189, 222, 255, 18), 1.0))
        painter.drawLine(
            int(left_padding), int(centre_y),
            int(self.width() - right_padding), int(centre_y),
        )
        painter.setPen(Qt.PenStyle.NoPen)

        for index, level in enumerate(self._levels):
            position = index / max(1, self.BAR_COUNT - 1)
            center_x = left_padding + (index + 0.5) * step
            height = 7.0 + level * 60.0
            color = self._bar_color(position)

            glow = QColor(color)
            glow.setAlpha(round(18 + level * 38))
            glow_rect = QRectF(
                center_x - bar_width / 2.0 - 2.4,
                centre_y - height / 2.0 - 2.4,
                bar_width + 4.8,
                height + 4.8,
            )
            painter.setBrush(glow)
            painter.drawRoundedRect(
                glow_rect,
                (bar_width + 4.8) / 2.0,
                (bar_width + 4.8) / 2.0,
            )

            fill = QColor(color)
            fill.setAlpha(round(122 + self._activity_mix * 118))
            rect = QRectF(
                center_x - bar_width / 2.0,
                centre_y - height / 2.0,
                bar_width,
                height,
            )
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, bar_width / 2.0, bar_width / 2.0)

            highlight = QColor(255, 255, 255, round(25 + self._activity_mix * 80))
            painter.setBrush(highlight)
            painter.drawEllipse(
                QRectF(
                    center_x - bar_width * 0.18,
                    rect.top() + 1.2,
                    bar_width * 0.36,
                    bar_width * 0.36,
                )
            )
