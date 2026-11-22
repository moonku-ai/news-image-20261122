# The World in Seven Frames — 22 November 2026

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/moonku-ai/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/moonku-ai/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

A [make.fun](https://make.fun/bounty/news-image-20261122) bounty entry: a pure Python (stdlib only) program that draws one
1024x1024 image summing up the world news of Sunday 22 November 2026 and
writes it to `/output/entry.png`.

## What the image shows

A dark newsroom video wall — "THE WORLD IN SEVEN FRAMES" — dated
**SUNDAY 22 NOVEMBER 2026**, with seven stories across seven fields:

1. **COP31 NEARS A DEAL** (climate) — new package agreed in Antalya; approval
   vote 06:00 GMT Sunday; fossil-fuel wording settled after two days overtime.
2. **TRUMP MEETS ZELENSKY** (diplomacy) — 20-point peace plan in Florida;
   territory and Zaporizhzhia still unresolved.
3. **ANTHROPIC SLIDES** (markets) — shares −8.5% to near its $83 IPO price;
   Nasdaq −5.6% Friday as the AI rally halts.
4. **ESTONIA SHUTS BORDER** (Europe) — road crossings to Russia close 1 Dec
   for 6 months; Moscow calls it a "new Iron Curtain".
5. **PERU SHAKEN** (disaster) — magnitude 6.9 quake in the Andes; no
   casualties reported.
6. **MISSILES OVER RIYADH** (Middle East) — Saudi intercepts 3 Houthi
   missiles; 2nd strike on Riyadh in days.
7. **FBI DATABASE HACKED** (cyber) — crime database probed; 2nd intrusion
   in months.

Plus an "ALSO TODAY" ticker (South Africa votes; Australia ends England's
T20 streak; Modi opens Nitish Setu; Cyclone Akvan; 128 nations draft
robot-weapon rules) and a sources footer.

All stories were verified against at least two news sources on 22 Nov 2026
(before the image was drawn). Sources: Reuters, AP, BBC, CNN, AFP, UN News,
ICJ.

## Run it

```sh
python3 main.py            # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

No third-party packages, no network. Two runs write byte-identical files.

## Tests

```sh
python3 -m unittest test_main -v   # 10 tests: PNG validity, determinism,
                                   # font coverage, layout fit, stdlib only
```

## Technique

Hand-written PNG encoder (zlib) + a 5x7 bitmap font + a small shape /
pictogram rasterizer (globe, flags, plunging chart, border barrier, seismic
zigzag, rocket, padlock), all in `main.py`. The image is drawn by the
program — no photos, no generated image.

## License

MIT — see LICENSE.
