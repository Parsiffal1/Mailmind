# MailMind Demo GIFs

These README-safe assets are generated from sample data only. They do not contain real Gmail messages, OAuth credentials, or attachments.

```md
![MailMind hero animation](docs/assets/mailmind-hero.gif)

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

![MailMind indexed sources and settings](docs/demo/gifs/documents_and_settings.gif)

![MailMind privacy settings](docs/demo/gifs/privacy_settings.gif)
```

## Generated Files

- `docs/assets/mailmind-hero.html`
- `docs/assets/mailmind-hero.gif`
- `docs/demo/gifs/hero_ai_search.gif`
- `docs/demo/gifs/documents_and_settings.gif`
- `docs/demo/gifs/privacy_settings.gif`

## Regenerate

```bash
export NODE_PATH=/root/.hermes/hermes-agent/node_modules
node /tmp/huashu-design/scripts/render-video.js docs/assets/mailmind-hero.html --duration=12 --width=1920 --height=1080 --readytimeout=8 --fontwait=1.5
ffmpeg -y -loglevel error -i docs/assets/mailmind-hero.mp4 -vf "fps=20,scale=820:-1:flags=lanczos,palettegen=stats_mode=diff" docs/assets/.mailmind-hero-palette.png
ffmpeg -y -loglevel error -i docs/assets/mailmind-hero.mp4 -i docs/assets/.mailmind-hero-palette.png -lavfi "fps=20,scale=820:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" docs/assets/mailmind-hero.gif
rm -f docs/assets/.mailmind-hero-palette.png docs/assets/mailmind-hero.mp4 docs/assets/mailmind-hero-60fps.mp4
node scripts/capture_demo_screenshots.mjs
python scripts/create_demo_gifs.py
```
