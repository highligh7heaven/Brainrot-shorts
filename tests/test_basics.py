import unittest

from brainrot import captions, story


class StoryTests(unittest.TestCase):
    def test_sample_story_is_tidy(self):
        s = story.sample_story()
        ids = {c["id"] for c in s["characters"]} | {"narrator"}
        for scene in s["scenes"]:
            for line in scene["lines"]:
                self.assertIn(line["who"], ids)
        self.assertIn("#shorts", s["hashtags"])

    def test_unknown_speaker_becomes_narrator(self):
        raw = story.sample_story()
        raw["scenes"][0]["lines"][0]["who"] = "Someone Else"
        tidy = story.check_story(raw, raw["brief"])
        self.assertEqual(tidy["scenes"][0]["lines"][0]["who"], "narrator")

    def test_unspeakable_lines_dropped(self):
        raw = story.sample_story()
        raw["scenes"][0]["lines"].append({"who": "narrator", "text": "...", "delivery": "normal"})
        tidy = story.check_story(raw, raw["brief"])
        self.assertNotIn("...", [l["text"] for l in tidy["scenes"][0]["lines"]])

    def test_missing_tags_added(self):
        raw = story.sample_story()
        raw["hashtags"] = ["funny"]
        self.assertEqual(story.check_story(raw, raw["brief"])["hashtags"], ["#funny", "#shorts", "#brainrot"])


class CaptionTests(unittest.TestCase):
    def test_one_word_per_event_without_overlap(self):
        words = [("She", 0.0, 0.2), ("poured", 0.25, 0.5), ("GOLD.", 0.55, 0.9)]
        ass = captions.build(words, 2.0)
        lines = [l for l in ass.splitlines() if l.startswith("Dialogue") and ",Word," in l]
        self.assertEqual(len(lines), 3)
        self.assertIn("0:00:00.25", lines[0])          # first word ends when the next starts
        self.assertIn(captions.YELLOW, lines[2])       # dramatic word is highlighted
        self.assertTrue(lines[2].endswith("GOLD"))     # punctuation trimmed

    def test_money_is_dramatic(self):
        self.assertTrue(captions.is_dramatic("$10B"))
        self.assertFalse(captions.is_dramatic("table"))


if __name__ == "__main__":
    unittest.main()
