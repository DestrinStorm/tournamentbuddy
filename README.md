# tournamentbuddy
Tournament management software for a variety of tabletop gaming systems
Hosted on Google App Engine running in Python

TODO list:
Look at storage, can we have a way of moving tournaments?
Add players after it starts?  Or at least a way of deleting rounds
Add a sort to the table list to order by 'matches won' tables (2 score, 1 score etc)
Manual repairing should check they aren't playing on a previous table
Round timings for non timed turns

Release notes:
Players can now be swapped into the bye seat
non entry of CP/Points destroyed on results screen now defaults those entries to 0
Put in a fix for sneaky people who try to use the back button and break things
fix 'paired down' flag for manual swaps - currently it will STILL LET YOU swap a previously paired down player into a new seat where they are once again paired down.  Technically this is against Steamroller rules but I figured flexibility is good?  I've added a 'paired down T/F?' column so you can check whether this is a thing you are about to do