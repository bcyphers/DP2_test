# DP2 Test Suite
This is a system to test our DP2 schemes. datacenter.py has the main code for
the virtual datacenter, and machine.py has the code for the virtual machine and
physical machine simulation classes. To try it, run 'python real\_test.py' and
watch \- it fills the data center with 200 randomly-generated VMs, then adds 10
users with 20 VMs each to the network and lets them run to completion. Other 
schemes can be run with greedy\_test.py, straggler\_test.py, and pairs\_test.py.

### Outline of datacenter properties:
 - machines has 288 Machine objects indexed by ID - 1/4th the actual number. 
 - VMs stores all VirtualMachine objects which have been added to the data
   center indexed by ip address
 - users stores some statistics about user time and completion, indexed by an 
   integer user ID
 - agg\_links stores all the links from group routers to aggregate routers.
   This is a dictionary, indexed by tuples of (group\_id, aggregate\_id) which
represent links, and pointing to lists of (VM1, VM2) connections active on the
links.  Since traffic is divided evenly among the connections, the throughput
on a link can be calculated by (total throughput) / (number of connections).
 - core\_links stores all the links from aggregate routers to the core router
   (which is represented as one object - see below), and is structured in the
same way as agg\_links except that each link is only indexed by aggregate
router number.
 - time is the last time the data center was brought up-to-date.
 
### Flow of the DataCenter class:
 - Methods starting with a normal letter (like place()) are public API calls,
   and methods starting with an underscore are private. 
 - The whole system does not actually calculate things in real time, but every
   time a function call changes something in the data center or requests
up-to-date information, the whole center brings itself up-to-date with
\_update.
 - \_update calculates the time (mttc) when the next connection among VMs which
   will terminate. If that time has already passed, it calls
\_roll\_forward(mttc), which distributes data among all the currently active
connections, and then re-evaluates the system. It continues to do this until it
reaches the current time.
 - \_roll\_forward accepts delta time as an argument. It loops over all active
   connections, computes the throughput on the link for each, and then
transfers (delta time * throughput) worth of data on each connection.
 - \_add\_link and \_remove\_link do about what you'd think they do
 - \_get\_link\_speed calculates througput in MBPS between any two \_groups\_.
 - draw\_status clears the terminal screen and prints out a summary of the
   system at any given time. Inside the method are a ton of hacky generator
expressions, please ignore.

### Flow of the Server class (in test.py):
 - Servers are initialized with a user ID, a acenter object, number, _n_, of
   virtual machines, and a noterh number, max\_data, indicating the maximum
amount of data any VM should have to transfer to any ohter VM. 
 - The start() function generates a B matrix and places the VMs around the data
center according to whatever logic the server's scheme uses.
 - The loop() function updates the state of the data center, re-places VMs if
necessary, and checks for completion. 
 - on\_complete() is a callback function that is passed to each VM for execution
when the VM's data transfers are finished. The default version just checks to 
see if _all_ transfers are complete, and removes the VM if possible.

### And remember:
 - "Losers visualize the penalties of failure. Winners visualize the rewards of
   success." \- Unknown
 - "The more you want to get something done, the less you call it work" -
   Richard Bach
 - "To accomplish great things we must not only act, but also dream; not only
   plan, but also believe" - Anatole France
 - "If you're going through hell, keep going" - Winston Churchill
 - "Sucking at something is the first step to being kinda good at something" -
   Jake the dog
