# Tally

Tally is a short color-betting game.

## Deck

There are 12 cards:

- 4 red
- 4 blue
- 4 yellow

The deck is shuffled once at the start of the game. Cards are drawn in that order.

## Turn

Each turn you bet the color of the **next** card.

Write your bet to `/app/bet.json` as JSON:

```json
{ "color": "red" }
```

Allowed colors: `red`, `blue`, `yellow`.

## Score

After you bet, the next card is revealed.

- Match the color: **1 point**
- Miss: **0 points**

There are 12 turns (one per card). Your total is the sum of the turn scores (max 12).

## View

`/app/view.txt` shows the current turn and the last revealed card (if any).
It does not list the full discard pile or the remaining deck.
