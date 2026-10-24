# Brainrot Shorts

Makes vertical "AI fruit drama" YouTube Shorts automatically and sends each
one to the Content Factory Telegram bot, ready to upload by hand.

## What happens in one run

1. **Story:** Claude writes a 35–50 second drama (narrator plus characters,
   hook in the first line, cliffhanger at the end) and the title, description
   and hashtags.
2. **Voices:** free Microsoft Edge voices, a different one per character, with
   the time of every word.
3. **Pictures:** OpenAI draws one reference picture per character, then about
   6 movie-style scenes that reuse those references.
4. **Video:** ffmpeg slowly zooms and pans each scene and burns in big
   one-word-at-a-time captions. Output is a 1080×1920 MP4 under 60 seconds.
5. **Delivery:** the video goes to Telegram as a file (full quality),
   followed by the title, then the description and hashtags.

## Series, trends and memory

Stories run as series of 3–4 parts with the same characters, character
pictures and narrator ("PART 2" shows on screen). A new series starts from
your own idea or from today's Google Trends. `state/memory.json` remembers
the running series, past stories (so none repeat) and which scheduled times
already had their video. Every real run saves it back to the repository.

## Schedule

The workflow checks every hour. It makes a video when one of your daily times
passed less than 3 hours ago and hasn't had its video yet, which also covers
GitHub starting late and retries after a failed run. Change the times without
touching code: Settings → Secrets and variables → Actions → **Variables**:

| Variable | Default |
|---|---|
| `POST_TIMES` | `8am, 1pm, 7pm` |
| `TIMEZONE` | `America/Vancouver` |

## Running it

GitHub app → **Actions** → **Brainrot Shorts** → **Run workflow**. You can
type an idea, or tick **test** for a built-in story that isn't sent to Telegram.

## Secrets (Settings → Secrets and variables → Actions)

| Name | What it is |
|---|---|
| `ANTHROPIC_API_KEY` | writes the stories |
| `OPENAI_API_KEY` | draws the pictures |
| `TELEGRAM_BOT_TOKEN` | the Content Factory bot's token |
| `TELEGRAM_CHAT_ID` | your Telegram user id |

No key is ever written in the code.

## Code map

| File | Job |
|---|---|
| `brainrot/story.py` | story prompt, format and test story |
| `brainrot/cast.py` | narrator and character voices |
| `brainrot/voice.py` | speech and word timings |
| `brainrot/images.py` | character references and scene pictures |
| `brainrot/captions.py` | one-word captions (.ass) |
| `brainrot/video.py` | zoom and pan slideshow, final MP4 |
| `brainrot/telegram.py` | delivery |
| `brainrot/memory.py` | series and past stories |
| `brainrot/trends.py` | today's Google Trends |
| `brainrot/schedule.py` | daily times check |
| `brainrot/main.py` | runs everything in order |

Tests: `python -m unittest`
