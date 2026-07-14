---
name: chat-formatting-widgets
description: Governs the custom markdown widgets rendered in the QuantumByte chat interface. This includes the inline highlight-mark span (use on every question the user must answer). You must check this skill on every reply to format highlights.
---

# Chat Formatting & Markdown Widgets

Your chat replies render through the QB Markdown Renderer, which accepts ordinary markdown plus a small allow-list of inline HTML widgets. Anything outside this list is stripped or rendered literal.

## Inline Highlight (Yellow Marker)
- **Syntax**: `<span class="highlight-mark">text</span>`
- **Mandatory Rule**: Wrap the core question phrase in `<span class="highlight-mark">...</span>` whenever your message contains a question the user must answer (e.g. atomic child prompt, confirmation).
- **Limit**: Highlight at most ONE phrase (3-8 words) per message. Do not highlight whole sentences.
