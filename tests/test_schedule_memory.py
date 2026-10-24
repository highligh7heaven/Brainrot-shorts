import unittest
from datetime import datetime, timezone
from unittest import mock
from zoneinfo import ZoneInfo

from brainrot import memory, schedule

VAN = ZoneInfo("America/Vancouver")


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class ScheduleTests(unittest.TestCase):
    def test_parse_times(self):
        self.assertEqual(schedule.parse_times("8am, 1:30pm, 19:00, 12am, junk"),
                         [(0, 0), (8, 0), (13, 30), (19, 0)])

    def test_due_shortly_after_slot(self):
        # 8:20am Vancouver on 24 Oct 2026 (UTC-7)
        slot = schedule.due_slot([(8, 0), (13, 0)], set(), utc(2026, 10, 24, 15, 20), VAN)
        self.assertEqual(slot, "2026-10-24 08:00")

    def test_not_due_twice(self):
        slot = schedule.due_slot([(8, 0)], {"2026-10-24 08:00"}, utc(2026, 10, 24, 15, 20), VAN)
        self.assertIsNone(slot)

    def test_catches_up_late_run_but_not_after_3_hours(self):
        self.assertEqual(schedule.due_slot([(8, 0)], set(), utc(2026, 10, 24, 17, 50), VAN), "2026-10-24 08:00")
        self.assertIsNone(schedule.due_slot([(8, 0)], set(), utc(2026, 10, 24, 18, 30), VAN))

    def test_late_evening_slot_seen_after_midnight_utc(self):
        # 7pm Vancouver slot checked at 02:30 UTC the next day (7:30pm local)
        self.assertEqual(schedule.due_slot([(19, 0)], set(), utc(2026, 10, 25, 2, 30), VAN), "2026-10-24 19:00")


class MemoryTests(unittest.TestCase):
    def test_series_runs_its_parts_then_ends(self):
        mem = {"series": None, "history": [], "done_slots": []}
        series = memory.new_series("s1")
        series["total"] = 2
        script = {"title": "T", "series_title": "Saga", "summary": "x", "cliffhanger": "c", "narrator": 4,
                  "characters": [{"id": "a", "name": "A", "look": "l", "voice": "man"}]}
        with mock.patch.object(memory, "shutil"):
            memory.record(mem, script, series)
            self.assertIs(memory.continuing(mem), series)
            self.assertEqual(series["narrator"], 4)
            memory.record(mem, dict(script, summary="y"), memory.continuing(mem))
        self.assertIsNone(mem["series"])
        self.assertEqual(len(mem["history"]), 2)
        self.assertIn("Saga (part 2): y", memory.avoid_list(mem))

    def test_slots_marked(self):
        mem = {}
        memory.mark_slot(mem, "2026-10-24 08:00")
        memory.mark_slot(mem, "")
        self.assertEqual(mem["done_slots"], ["2026-10-24 08:00"])


if __name__ == "__main__":
    unittest.main()
