# tournamentbuddy
Tournament management software for a variety of tabletop gaming systems
Hosted on Google App Engine running in Python

TODO list:
Look at storage, can we have a way of moving tournaments? - Arch change, requires removing 'userID' as a parent and moving it into the properties of a tournament object...Probably worth doing but significant effort
Add a sort to the table list to order by 'matches won' tables (2 score, 1 score etc)
Manual repairing should check they aren't playing on a previous table
Round timings for non timed turns

Release notes:
Adding players is supported after round 1 has started
    If you are currently even, they are slotted into the bye seat
    If there is a byed player, the next person added is matched to the byed player and the bye is cleared
    This can theoretically happen as many times as you need
    After round 2 pairings have been done, the option to add players once again vanishes...seems like they would be too late at this point
