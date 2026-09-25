# Heads-up no-limit Texas Hold'em

You play one opponent. Blinds are **5** (small) and **10** (big). You both start
with **1000** chips. Stacks persist from hand to hand. The score is earnings:
your chips minus 1000.

Each Harbor step is one hand. The button rotates after every hand. In
heads-up, the button posts the small blind and acts first before the flop.
After the flop, the big blind acts first.

You may fold, check, call, or raise. `poker act raise 30` means raise **to** 30
chips. A raise amount of at least the listed minimum is required, unless you
are all-in.

The opponent plays a fixed style for the whole match. You do not see their
hole cards until a showdown.

Commands:

```text
poker status
poker act fold
poker act check
poker act call
poker act raise 30
```

`status` does not advance the hand. Invalid commands do not advance the hand.
After the hand ends, stop. Do not try to start the next hand.
