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
node scripts/render_true30_gif.cjs docs/assets/mailmind-hero.html --duration=10.5 --fps=30 --width=1920 --height=1080 --gif-width=820
rm -f docs/assets/mailmind-hero.mp4
node scripts/capture_demo_screenshots.mjs
python scripts/create_demo_gifs.py
```
