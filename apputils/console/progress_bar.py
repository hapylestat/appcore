# coding=utf-8
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# Copyright (c) 2015 Reishin <hapy.lestat@gmail.com>


import sys
import time
import os
from apputils.console import get_terminal_size
from apputils.utils import safe_format

"""
    Template description:
      begin_line - here would be placed character of the begin line
      text - caption of the progress
      status - similar to caption, but could be changed thought iteration
      end_line - used mostly in situation, when status is on right side, should fix issues
       with different len of status messages
      filled - part of progress bar which represent filled part
      reverse_filled - part of progress bar which represent reversed filled part
      empty - part of progress bar which represent not filled part
      value - current value
      max - max value
      unit_per_sec - amount of units per second
      percents_done - percents done

"""


class ProgressBarFormat(object):
  PROGRESS_FORMAT_DEFAULT = "{begin_line}{text} {percents_done:>3}% [{filled}{empty}] {value}/{max}  {items_per_sec} i/s"
  PROGRESS_FORMAT_SHORT = "{begin_line}{text} {percents_done:>3}% [{filled}{empty}] {value}/{max}"
  PROGRESS_FORMAT_SIMPLE = "{begin_line}{text} [{filled}{empty}] {percents_done:>3}%"
  PROGRESS_FORMAT_STATUS = "{begin_line}{text}: |{filled}{empty}| {percents_done:>3}%  {value}/{max}   [{status}]{end_line}"
  PROGRESS_FORMAT_STATUS_SIMPLE = "{begin_line}|{filled}{empty}| {percents_done:>3}%   [{status}]{end_line}"
  PROGRESS_FORMAT_INFINITE_SIMPLE = "{begin_line} {filled}{empty} [text] {empty}{reverse_filled}"


class CharacterStyles(object):
  default = (" ", "=")
  simple = ("-", "#")
  graphic = ("░", "█")


class ProgressBarOptions(object):
  def __init__(self, character_style=CharacterStyles.default, progress_format=ProgressBarFormat.PROGRESS_FORMAT_DEFAULT):
    """
    :type character_style tuple
    :type progress_format str
    """
    self._fill_char = character_style[1]
    self._blank_char = character_style[0]
    self._progress_format = progress_format

  @property
  def fill_char(self):
    return self._fill_char

  @property
  def blank_char(self):
    return self._blank_char

  @property
  def progress_format(self):
    return self._progress_format


class _ProgressBarTiming(object):
  def __init__(self):
    self.__max_value = None
    self.__unit_per_sec = None
    self.__unit_per_sec_prev = None

    #  timers
    self.__prev_tick = None

  def init_timer(self, max_value):
    """
    :type max_value int
    """
    self.__max_value = max_value
    self.__prev_tick = time.time()
    self.__unit_per_sec = 0
    self.__unit_per_sec_prev = 0

  def tick(self, unit_value):
    """
    :type unit_value int
    """
    total_secs = round(time.time() - self.__prev_tick)
    if total_secs >= 1:
      self.__unit_per_sec = unit_value / total_secs - self.__unit_per_sec_prev
      self.__unit_per_sec_prev = unit_value
      self.__prev_tick = time.time()

  @property
  def unit_per_sec(self):
    """
    :rtype int
    """
    return int(self.__unit_per_sec)


class ProgressBarStatus(object):
  stopped = 0
  started = 1


class ProgressBar(object):
  def __init__(self, text, width, options=ProgressBarOptions()):
    """
    Create ProgressBar object

    :argument text Text of the ProgressBar
    :argument options Format of progress Bar

    :type text str
    :type width int
    :type options ProgressBarOptions
    """
    self._text = text
    self._status_msg = ""
    self._width = width
    self._max = 0
    self._console_width = get_terminal_size(fallback=(80, 24))[0]
    self._value = None
    self._timer = _ProgressBarTiming()
    self._begin_line_character = '\r'
    self._options = options
    self._infinite_mode = None
    self._infinite_position = None
    self._infinite_width = 1
    self.stdout = sys.stdout
    self._status = ProgressBarStatus.stopped

  @property
  def value(self):
    return self._value

  @property
  def status(self):
    return self._status

  @property
  def _width(self):
    """
    :rtype float
    """
    return self.__width

  @_width.setter
  def _width(self, value):
    """
    :type value float
    """
    self.__width = float(value)

  @property
  def _max(self):
    """
    :rtype float
    """
    return self.__max

  @_max.setter
  def _max(self, value):
    """
    :type value float
    """
    self.__max = float(value)

  def start(self, max_val):
    """
    :arg max_val Maximum value
    :type max_val int
    """
    self._timer.init_timer(max_value=max_val)

    self._infinite_mode = max_val <= 0
    self._infinite_position = 0

    self._max = max_val
    self._fill_empty()
    self._value = 0
    self.progress(0)
    self._status = ProgressBarStatus.started

  def _calc_percent_done(self, value):
    """
    :type value float
    """
    return int(value / self._max * 100)

  def _calc_filled_space(self, percents):
    """
    :type percents int
    """
    return int((self._width / 100) * percents)

  def _calc_empty_space(self, percents):
    """
    :type percents int
    """
    return int(self._width - self._calc_filled_space(percents))

  def _fill_empty(self):
    data = " " * (self._console_width - len(self._begin_line_character))
    self.stdout.write(self._begin_line_character + data)
    self.stdout.flush()

  def progress(self, value, new_status=None):
    """
    :type value int
    :type new_status str
    """
    space_fillers = 0

    if new_status is not None:
      # if new text is shorter, then we need fill previously used place
      space_fillers = len(self._status_msg) - len(new_status) if self._status_msg and len(self._status_msg) - len(new_status) > 0 else 0
      self._status_msg = new_status

    if not self._infinite_mode and value > self._max:
      self._infinite_mode = True
      self._fill_empty()

    self._timer.tick(value)

    if not self._infinite_mode:
      percent_done = self._calc_percent_done(value)
      filled = self._options.fill_char * int(self._calc_filled_space(percent_done))
      empty = self._options.blank_char * int(self._calc_empty_space(percent_done))
    else:
      percent_done = 100
      self._infinite_position = 1 if self._infinite_position + self._infinite_width >= self._width else self._infinite_position + 1
      filled = "%s%s" % (self._options.blank_char * (self._infinite_position - self._infinite_width), self._options.fill_char * self._infinite_width)
      empty = self._options.blank_char * int(self._width - self._infinite_position)

    kwargs = {
      "begin_line": self._begin_line_character,
      "text": self._text,
      "status": self._status_msg,
      "end_line": " " * space_fillers,
      "filled": filled,
      "reverse_filled": filled[::-1],
      "empty": empty,
      "value": int(value),
      "max": int(self._max),
      "items_per_sec": self._timer.unit_per_sec,
      "percents_done": percent_done
    }

    self.stdout.write(safe_format(self._options.progress_format, **kwargs))
    self.stdout.flush()

  def progress_inc(self, step=1, new_status=None):
    """
    :type step int
    :type new_status str
    """
    self._value += step
    self.progress(self._value, new_status=new_status)

  def reset(self):
    self._status = ProgressBarStatus.stopped
    self._max = 0
    self._value = 0
    self.progress(0)

  def stop(self, hide_progress=False, new_status=None):
    """
    :arg hide_progress Hide progress bar
    :type hide_progress bool
    :type new_status str
    """

    self._status = ProgressBarStatus.stopped
    if hide_progress:
      sep = " - "
      if new_status is None:
        new_status = sep = ""

      kwargs = {
        "begin_line": self._begin_line_character,
        "text": self._text,
        "new_status": new_status,
        "sep": sep,
        "fill_space": " " * (self._console_width - len(self._text) - len(sep) - len(new_status) - len(os.linesep))
      }
      self.stdout.write("{begin_line}{text}{sep}{new_status}{fill_space}".format(**kwargs))
    else:
      self.progress(int(self._max), new_status=new_status)

    self.stdout.write(os.linesep)
