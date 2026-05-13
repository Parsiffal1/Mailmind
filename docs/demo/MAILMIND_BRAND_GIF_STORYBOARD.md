# MailMind Brand Hero GIF Storyboard

目标：重新设计一个不依赖 demo 数据的 GitHub README hero GIF。新版本不使用无语义线条装饰，而是用一个清晰的产品故事表达 MailMind：

> Gmail messages go in. MailMind turns them into tasks, searchable knowledge, and privacy-aware AI answers.

## Design References

- SaaS hero visual should quickly communicate what the product does and make the product concrete, not just decorative.
- Motion should explain workflow/state change. It should guide attention and clarify what changed.
- For README, GIF should remain lightweight and readable as a static final frame.

## Visual System

- Background: warm off-white, very subtle grid only as workspace texture.
- Main object: MailMind logo as the processing hub.
- Input objects: three compact email cards, not random lines.
- Output objects: three capability cards.
- Motion language:
  - email cards enter from left
  - they compress into the MailMind hub
  - a scan ring indicates processing
  - output cards appear on the right
  - final title locks up below the logo

## Shot 1: Empty Local Workspace

Time: `0.0s - 0.8s`

Frame:
- Calm light background.
- No decorative motion except a soft card shadow area.

Purpose:
- Start clean. No meaningless visual clutter.

## Shot 2: Gmail Inputs Arrive

Time: `0.8s - 2.1s`

Frame:
- Three small email cards slide in from the left.
- Each card has a subject-like line:
  - `deadline`
  - `reply`
  - `attachment`
- Cards stack near the MailMind logo.

Purpose:
- Make the input explicit: Gmail messages.

## Shot 3: MailMind Processing

Time: `2.1s - 3.4s`

Frame:
- Email cards shrink/fade into the logo.
- Logo gets a soft mint scan ring.
- A small status pill appears: `Local-first processing`

Purpose:
- Explain the product mechanism without showing real UI or data.

## Shot 4: Structured Outputs

Time: `3.4s - 5.2s`

Frame:
- Three cards appear to the right of the logo:
  - `Tasks`
  - `AI Search`
  - `PII Guard`
- Each card has a one-line description:
  - `Extract deadlines`
  - `Grounded answers`
  - `Redact before LLM`

Purpose:
- Show what MailMind produces from email input.

## Shot 5: Brand Lockup

Time: `5.2s - 7.0s`

Frame:
- Logo moves slightly upward.
- `MailMind` title appears.
- Subtitle appears:
  - `Local-first Gmail intelligence`
- Input and output cards stay visible as a clear mini pipeline.

Purpose:
- Final frame works as a static README hero.

## What Changed From Previous Version

- Removed random horizontal lines and dots.
- Replaced them with email cards and output cards that explain the product.
- Animation now has a readable cause-effect sequence:
  - email input -> MailMind processing -> structured AI outputs.
- The GIF is no longer just a logo reveal; it communicates product value.
