# W4 browser QA

November 10, 2026. Real Chromium via Playwright CLI on Windows; local Python static
server on 127.0.0.1:18737. Frontend-design and Playwright skills were applied.

## Design review

The supplied interaction palette is retained: Paper #ffffff, Fog #eaf2f8,
Ink #17324d, Signal #2459a6, Landing #d6eee3, Alert #9c3045. Local Segoe UI /
Trebuchet typography is used. The board is the illustration: quiet white strips,
one explicit target flag, and a bounded landing zone. Desktop columns align near
the action area; narrow screens use a scrolling single column. No card grid,
external font, decorative word numbering or ambient motion was introduced.

Screenshot critique: target and zone have redundant text labels; the input focus
outline remains clear. Long words wrap at readable sizes and expand the board
rather than clipping. On narrow displays the input follows the stack in normal
flow, allowing scrolling without covering any word. Scores remain secondary.

## Observed results

- `node --test tests/web/client.test.mjs`: **6 passed**.
- Real browser start and submission using Enter; Play focuses the input. Rejection
  retains and selects the draft for correction. Help opens and Escape closes it.
- Browser smoke script passes keyboard start, submit, retry and Help; simulated IME
  composition blocks submission, then Enter works after composition ends.
- Frozen bottom-three receipt clears only its target, displays 100 authoritative
  points, focuses the final heading, and Play again starts a fresh sequence at 0.
- Reduced motion preserves immediate board/result state. 320 CSS px with 64-code-
  point unbroken W labels: **no horizontal overflow**. 200% CSS zoom at 1280 px:
  **no horizontal overflow**. Labels remain wrapped and readable.
- Browser reconnect script aborts the first command POST, returns unknown receipt,
  then accepts its exact retry: **two byte-identical POST payloads**. Pending
  polling resolves the recorded clear, unlocks input and clears the submitted draft.
  Reload retains the same game, draft and authoritative score.
- Initial QA caught a native fetch receiver binding error; fixed by binding the
  default fetch implementation. Final browser scripts pass after the fix.

## Captures

- [Desktop stack and focused entry](qa-desktop.png)
- [320 px rejection and input](qa-mobile.png)
- [320 px, 64-code-point labels, reduced motion](qa-long-labels.png)
- [200% zoom, long labels](qa-zoom.png)
- [Reconciled HTTP game after reload](qa-reconnected.png)

These are real browser captures. Long-label QA changes labels in intercepted
fixture responses only. Reconnect QA mocks the frozen HTTP envelope sequence;
it is not evidence of real-model integration or measured gameplay latency.
The rejected network request in reconnect QA intentionally emits a browser console
network error. No unhandled application error remains in the successful runs.

## Remaining acceptance

Physical mobile virtual-keyboard behavior, assistive-technology speech timing,
human understanding/enjoyment, and actual browser/server/model play remain W5
acceptance work. The browser tests do not establish the 100 ms latency target.
CSS zoom is a reproducible layout check, not an OS/browser zoom accessibility audit.
No independent accessibility audit or official competition result is claimed.
