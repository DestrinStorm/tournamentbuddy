# tournamentbuddy
Tournament management software for a variety of tabletop gaming systems
Hosted on Google App Engine running in Python

TODO list:
Manual repairing should check they aren't playing on a previous table
Round timings for non timed turns

Release notes:
(players schema update needed)
ID field for players
Notes field for players
dropped status for dropped players
Drop will now delete if in round 0 and drop if in any later rounds, maintaining player but removing them from the pairing algorithm for future
Tournament points visible in table seating...table
Sort order for the score tables is now: dropped status, score, sos, cp, pointsdest, entry number
There is now a check to ensure players cannot be seated against players they have already fought