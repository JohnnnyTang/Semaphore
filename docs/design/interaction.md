# Arcade interaction draft

Status: S1-W2-C, November 8, 2026. Design guidance for the W4 browser experiment;
no browser implementation or visual accessibility test has been performed yet.
Rules and ordering are defined in [gameplay.md](gameplay.md).

## Direction: send a signal, follow a word

Semaphore's visual center is one rising stack of word strips. A small flag-shaped
marker travels with the target, connecting the name to the act of signalling a
clue. The stack is the useful illustration: no hero artwork, dashboard card grid,
or abstract ambient motion. Put the target and clue action together and keep
score secondary. Word positions explain the rule, with a visibly bounded landing
zone beneath them. Labels are ordinary sentence case.

| Token | Value / purpose |
| --- | --- |
| Paper | `#FFFFFF`, main surface |
| Fog | `#EAF2F8`, quiet board background |
| Ink | `#17324D`, text and primary borders |
| Signal | `#2459A6`, target flag, focus ring and Send button |
| Landing | `#D6EEE3`, clear-zone background with Ink text |
| Alert | `#9C3045`, rejection text and full-stack boundary |

Use a locally available humanist system sans stack (`"Segoe UI", "Trebuchet MS",
sans-serif`) for expressive, readable words without a runtime font download.
Use normal tabular numerals for score and time. Proposed type sizes: 16 px minimum
input/body, 20–24 px board labels, 28 px target heading. Long labels may use 18 px
and wrap; do not shrink text below 16 px to make the stack fit. Verify contrast in
the implemented browser; palette selection alone is not an accessibility audit.

The first sketch used a colored strip for every row. Remove those colors: only the
target flag, landing zone and overflow boundary encode special state. This avoids
making all words compete for attention. Row numbering is useful only in the
post-clue explanation where it means semantic rank, never decorative enumeration.

## Desktop and narrow arrangements

At a comfortable desktop width, give the stack about 28 rem and put the target
and input in a neighboring column. Keep label text left aligned. Align both
columns at the bottom so the clue entry and landing zone share an obvious action
area. On a narrow viewport use one column, stack first, then a sticky input region
that does not cover the last rows. Allow page scrolling at zoom; never clip words
to preserve a fixed arcade canvas. Show occupied slots as a text count.

```text
Semaphore                                  Physical geography

  7 of 12 words                  Target: [flag] oxbow lake
  +--------------------------+   Guide the target into the bottom 3.
  |        empty slots       |
  | loess                    |   Score 400        Level 1
  | sand dune                |   Next word in 3 s
  | [flag] oxbow lake Target  |
  | glacier                  |   Your clue
  +--- Bottom 3: clear zone -+   [cut-off river bend            ]
  | delta                    |   [Send clue]
  | plateau                  |
  | valley                   |   Only the target clears.
  +--------------------------+
```

The displayed stack is top first, the server board is bottom first. The diagram
is an unranked example, not a fabricated semantic result. Real selected pack
labels replace these illustrative geography labels; use the pack's label, not its
hidden embedding text. Show context on pack details in later work.

```text
Semaphore                     Score 400
Target: [flag] oxbow lake
7 / 12 words            Next word in 3 s
+--------------------------------------+
| ... readable word rows ...            |
+--- Bottom 3: clear zone --------------+
| delta                                |
| plateau                              |
| valley                               |
+--------------------------------------+
Your clue
[cut-off river bend                    ]
[Send clue]
```

Target status uses the word “Target,” an outlined flag and heavier text as well as
color. Clear-zone status uses a boundary and text. A rejected clue shows an icon
with text and a reason. Do not rely on color, position, animation or sound alone.
When fewer than three words remain, all are in the clear zone; the label explains
“All remaining words are in the clear zone.”

## Keyboard and input behavior

The clue is a labeled single-line input. Enter submits except during IME
composition. Tab reaches Send, help and leave controls in visual order; no custom
tab trap. Initial focus goes to clue entry only after an explicit Play action.
Keep a strong visible focus outline. Do not refocus on every spawn or incoming
message. Escape dismisses help, never quits a game. Quit needs its own labeled
control; browser refresh/reconnect is allowed but does not pause the server clock.

During one pending command, retain submitted text read-only and disable Send.
Show “Ranking your clue…” with elapsed pending time only when useful. The board
continues to accept server spawns. Do not use an optimistic score, clear or target
switch. After a successful response, clear the submitted input, retain focus and
announce the new target. On rejection retain and select the clue for correction;
focus only if it was already in the game control. A read-only pending field must
still allow copying text. No hidden keyboard shortcuts are required.

| Situation | Player-facing response |
| --- | --- |
| Literal/alias/inflection/forbidden clue | “Try an association without the target word or its forbidden forms.” |
| Empty clue | “Type a clue first.” |
| Too long | “Use 120 characters or fewer.” with remaining count |
| Stale state | “The target changed. Check it before sending again.” Keep text; require a new explicit submit |
| Busy retry | Keep the existing pending indicator; never send a second inference |
| Inference failed | “That clue could not be ranked. Try again.” Keep text and use a new command ID |
| No target yet | “Next word arriving soon.” Disable submission, preserve draft text |
| Reconnecting | “Reconnecting. The game clock is still running.” Keep draft locally for this tab |

The 120-character limit uses server Unicode code-point semantics, not JavaScript
UTF-16 length. Client checks are hints; server reasons are authoritative. Never
display raw internal exception text or private account identifiers in errors.

## Make reordering understandable

On a ranked response, first show the words moving to their new positions, then
briefly mark the target's resulting rank, then remove it if it cleared. Suggested
total movement budget is 250–350 ms. Preserve stable entry DOM identity so the
target flag follows its word. Say “Target reached #2 — +100” on clear or
“Target reached #5. Try another association.” on a miss. These values come from
the server receipt, not DOM position. Show no fake precision for similarity.

Animation is presentation of an already-committed state. The next authoritative
revision can cancel or fast-forward it; never queue animations long enough to
hide arriving words. Pending input may unlock as soon as the response arrives,
independent of animation completion. The next command uses the current server
revision, including any intervening spawns, rather than the visibly animating
previous snapshot. A tiny persistent last-result line explains a canceled motion.

With `prefers-reduced-motion`, replace movement with immediate position updates
and a short static result line. Do not flash the overflow boundary. Use a polite
live region for clue results and target changes, and a single assertive game-over
announcement. Do not announce every timer tick or continuously narrate reordering.
The accessible list should use the same top-to-bottom order as the screen and
include “Target” and “in clear zone” text when applicable.

## Revisions, reconnect and ending

Store the latest applied revision. Ignore state portions older than that revision,
while allowing a receipt to resolve its matching pending command. Do not pair an
old receipt's target with a newer state's score. A higher revision snapshot replaces
the whole current state; gaps trigger a snapshot refresh rather than guessed
intermediate states. A duplicate receipt must never replay a +100 animation.

On reconnect, fetch current state and resolve the uncertain command ID. Retry the
exact payload only if appropriate; never change its ID to “make it work.” A new
clue is a new explicit action after state reconciliation. If the game ended while
disconnected, show the final server result immediately. Leaving/reloading a page
does not create a second completed result.

Game over replaces the input region with final score, reason and “Play again.”
Examples: “The stack filled up,” “Challenge complete,” or “Pack complete.” An
interrupted server session says “Game interrupted” without presenting an official
rank. Retry creates a new game; it never mutates the old score. Show a frozen final
stack for context, focus the result heading, and make the next action keyboard
reachable. Event identity and pack version stay visible in the result details.

## W4 implementation and acceptance

Vanilla HTML/CSS/JavaScript remains sufficient: one state store, transport adapter,
stable keyed rows, a small animation controller and a command receipt map. Keep
fixture transport separate from real transport through the W3 event contract.
No framework or network-hosted asset is justified by this scope.

W4 must test keyboard-only play, 320 CSS px width, 200% zoom, maximum 64-code-point
labels including unbroken words, mobile virtual-keyboard overlap, reduced motion,
IME Enter, stale/out-of-order events, duplicate result animation, disconnect while
pending, and game over during motion. Capture actual screenshots then; this draft
has no claimed visual QA. W5 must observe whether humans understand where words
move, why clues reject and why a near-deadline clue may lose to a spawn.
