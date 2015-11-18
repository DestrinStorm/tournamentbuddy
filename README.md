# tournamentbuddy
Tournament management software for a variety of tabletop gaming systems
Hosted on Google App Engined running in Python

TODO list:
System will no longer by the same player twice in a tournament and I believe will not pair a player down twice.
However, the matching algorithm is flawed:

example:
round 1: J(bye), P(win)vS, C(win)vA
round 2: S(bye), PvJ(ERROR) - system then tries to pair down C and match with A - impossible, they've already played
need to do the weighting for all rounds at once before generating pairings, or this will happen

Made good progress on matching algorithm, bye process is a little weird though - doesn't iterate fully, for no reason I can fathom!!

SOS calculations