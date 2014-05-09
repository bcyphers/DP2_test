import sys, math, random, time, itertools, threading
from machine import Machine, VirtualMachine
from collections import defaultdict

# If true, print extra info
VERBOSE = False

# Helper class for text colors
class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class DataCenter(object):
    GROUP_SIZE = 12
    NUM_GROUPS = 24
    NUM_MACHINES = GROUP_SIZE * NUM_GROUPS
    AGG_ROUTERS = 4
    THROUGHPUT = 10000.0  # in MBPS

    def __init__(self):
        # machines stores Machine objects indexed by machine_id
        self.machines = {i: Machine(i) for i in xrange(self.NUM_MACHINES)}

        # groups stores collections of machines indexed by group id
        self.groups = {i: [self.machines[j] for j in xrange(
            i * self.GROUP_SIZE, (i + 1) * self.GROUP_SIZE)] 
            for i in xrange(self.NUM_GROUPS)}

        # users keeps track of how much total time each user's VMs have used
        self.users = defaultdict(lambda: [0, 0, 0])

        # Links are represented as tuples: (lower level, upper level)
        # each link points to a list of the connections it currently serves.
        # For our purposes, the redundant routers are lumped into one.
        self.agg_links = {link: set() for link in 
                    [(i, int(i/6)) for i in range(self.NUM_GROUPS)]}
        self.core_links = {link: set() for link in range(self.AGG_ROUTERS)}

        # stores VMs indexed by IP address
        self.VMs = {}

        # this is the last time the system was updated
        self.time = time.time()
        self.start_time = self.time

        self.lock = threading.Lock()
        self.running = True

        print 'Data center initialized.'
    
    # Pause and play functions
    def pause(self):
        self.running = False

    def unpause(self):
        self.running = True

    # Place VM v on machine m, or return False if it is full
    def place(self, v, m):
        self._update()
        if v in self.VMs.values():
            raise Exception('VM ' + str(v.ID) + ' is already in the system.')
        if m not in self.machines:
            raise Exception('Not a valid machine ID')

        if self.machines[m].add_vm(v):
            ip = self._get_rand_ip()  # get an IP
            self.VMs[ip] = v  # index VM by IP
            v.machine = m
            v.ip = ip
            v.in_network = True

            counter = 0
            # add a link for each one of this VM's connections in the system
            for target in v.transfers:
                if target in self.VMs.values():
                    self._add_link(v, target)
                    counter += 1

            # check to see if other VMs in the system link to the new one
            for u in self.VMs.values():
                if v in u.transfers.iterkeys():
                    self._add_link(u, v)
                    counter += 1

            if VERBOSE:
                print 'Added VM with ip', ip, 'to machine', m
                print counter, 'links added'
            return ip
    
        # machine.add_vm() will return false if the machine is full
        if VERBOSE:
            print 'Tried to add to machine ' + str(m) + ', which is full'
        return False

    # Place VM v on a random machine. Return the machine's id and the VM's ip
    # if successful, or raise an error if the entire datacenter is full.
    def random_place(self, v):
        self._update()
        try:
            # Make a list of machines with some capacity, and choose randomly
            m = random.choice([i for i in range(self.NUM_MACHINES) 
                     if self.machines[i].occupancy() > 0])
        except IndexError:
            # If the list of valid machines is empty, the whole center is full
            raise Exception('No machines available')

        if VERBOSE:
            print 'Placing VM at random machine, id =', m
        return m, self.place(v, m)

    # Remove VM with ip from the network
    def remove(self, ip):
        v = self.VMs[ip]
        v.in_network = False

        # Remove all the active outgoing links from this VM
        for u in v.active_transfers.values():
            self._remove_link(v, u)

        # Find all incoming links and remove those, too
        it = [u for u in self.VMs.values() if v in u.active_transfers.values()]

        for u in it:
            self._remove_link(u, v)

        del self.VMs[v.ip]
        self.machines[v.machine].remove_vm(v)

    # Return the number of bytes left to transfer between u and v
    # TODO: find out what this actually means
    def progress(self, u, v):
        self._update()
        return u.to_transfer(v) + v.to_transfer(u)

    # Get the total amount of time a user has clocked
    def user_time(self, usr):
        self._update()
        return self.users[usr][0]

    # Return the number of slots open on machine m
    def machine_occupancy(self, m):
        self._update()
        return self.machines[m].occupancy()

    # Returns the throughput of the TCP connection from u -> v over
    # the last 100ms
    # TODO: figure out how - this gets the current link speed; not the same
    def tcp_throughput(self, u, v):
        self._update()
        return self._get_link_speed(self._get_group(u), self._get_group(v))

    # Prints out a full representation of everything in the system right now
    def draw_status(self):
        self._update()

        # clear the screen
        print chr(27) + "[2J"

        # print the system time
        print bcolors.HEADER + 'SYSTEM TIME: ' + bcolors.ENDC +\
                str(self.time - self.start_time) + '\n'

        # print link congestion stats: how many connections are using each?
        print bcolors.HEADER + 'LINK CONGESTION:' + bcolors.ENDC
        print bcolors.GREEN + ' * core links: ' + bcolors.ENDC +\
                    '; '.join(str(l) + ': ' + 
                    bcolors.YELLOW + str(len(num)) + bcolors.ENDC 
                    for l, num in self.core_links.items())

        print bcolors.GREEN + ' * aggregate links:\n   ' + bcolors.ENDC +\
            '\n   '.join(
                    '; '.join(str(l[0]) + '<->' + str(l[1]) + ': ' + 
                        bcolors.YELLOW + str(len(num)) + bcolors.ENDC
            for l, num in sorted(self.agg_links.items()) if l[1] == i) 
            for i in range(self.AGG_ROUTERS)) 

        # print the number of VMs in each group
        print bcolors.HEADER + '\nTOTAL VMs BY GROUP:' + bcolors.ENDC
        print '   ' + '\n   '.join(
                '  '.join(str(g) + ': ' + 
                    bcolors.YELLOW + 
                        str(sum(len(m.VMs) for m in self.groups[g])) +
                    bcolors.ENDC
                    for g in self.groups if int(g/6) == i) 
                for i in range(self.AGG_ROUTERS))

        # calculate some user stats
        for u in self.users:
            vms = [v for v in self.VMs.values() if v.user == u]
            try:
                pct = int(sum(v.total_data - sum(v.transfers.values())
                    for v in vms) / sum(v.total_data for v in vms) * 100)
            except:
                pct = 100
            
            done = sum(v.total_data - sum(v.transfers.values()) for v in vms)
            total = sum(v.total_data for v in vms)

            self.users[u][1] = str(len(vms))
            self.users[u][2] = str(int(done)) + '/' + str(total) + ' MB = ' + str(pct) + '%'

        # print some stats for each user
        print bcolors.HEADER + '\nUSER: TIME, VMs, % COMPLETION:' +\
                bcolors.ENDC
        print '   ' + '\n   '.join(
                'ID ' + str(usr) + ': ' + 
                bcolors.YELLOW + 
                str(val[0]) + ', ' + val[1] + ', ' + val[2] +
                bcolors.ENDC 
                for usr, val in self.users.items() if usr >= 0)

    # Get a random, unused ip for a VM
    def _get_rand_ip(self):
        # append 4 random bytes, with periods, in a string
        rand_ip = lambda: '.'.join([str(random.randrange(256)) 
                                    for i in range(4)])
        ip = rand_ip()
        while ip in self.VMs:  # try until we find one we haven't used
            ip = rand_ip()
        return ip
    
    # What group is this VM in? 
    def _get_group(self, vm):
        return int(vm.machine / self.GROUP_SIZE)

    # Add a link between two machines
    def _add_link(self, vm1, vm2):
        m1 = vm1.machine
        m2 = vm2.machine
        g1 = self._get_group(vm1)
        g2 = self._get_group(vm2)

        vm1.activate_transfer(vm2, vm2.ip)

        if g1 == g2:  # Don't add anything if they're in the same group
            return

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # Add the vm connection to the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].add((vm1.ip, vm2.ip)) 
        self.agg_links[(g2, ag2)].add((vm1.ip, vm2.ip)) 

        # Add the connection to the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].add((vm1.ip, vm2.ip))
            self.core_links[ag2].add((vm1.ip, vm2.ip))

    # Delete a link between two machines
    def _remove_link(self, vm1, vm2):
        m1 = vm1.machine
        m2 = vm2.machine
        g1 = self._get_group(vm1)
        g2 = self._get_group(vm2)

        vm1.deactivate_transfer(vm2.ip)

        if g1 == g2:
            return

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # remove the connection from the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].remove((vm1.ip, vm2.ip)) 
        self.agg_links[(g2, ag2)].remove((vm1.ip, vm2.ip)) 

        # remove the connection from the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].remove((vm1.ip, vm2.ip))
            self.core_links[ag2].remove((vm1.ip, vm2.ip))

    # What is the throughput (in MBPS) between two groups?
    # This assumes that all connections are given equal speeds
    def _get_link_speed(self, g1, g2):
        if g1 == g2:
            return self.THROUGHPUT

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # hacky 1-liner to grab all links
        links = [self.agg_links[(g1, ag1)],
                 self.agg_links[(g2, ag2)]] +\
                ([self.core_links[ag1], self.core_links[ag2]] \
                  if ag1 != ag2 else [])

        # count the connections on all the links between g1 & g2, 
        # and take the max
        max_connects = max(len(link) for link in links)

        # we can't actually have throughput greater than 10 mbps
        return 2 * self.THROUGHPUT / max(max_connects, 2)

    # Update the state of the data center
    def _update(self):
        if not self.running:
            return

        now = time.time()
        delta_t = now - self.time
        mttc = float('inf')  # min time to completion
        
        vms = self.VMs.values()
        for u in vms:
            if not u.in_network:
                self.remove(u.ip)
            for v in u.active_transfers.values():
                amt = u.transfers[v]
                tp = self._get_link_speed(
                        self._get_group(u), self._get_group(v))
                mttc = min(mttc, amt / tp)

        # If the first connection would have finished by now, roll forward
        # to the point in time that it ended, and recalculate stuff
        if mttc < delta_t:
            self._roll_forward(mttc)
            self._set_time(self.time + mttc)
            self._update()
        else:  # Otherwise, roll forward to the present
            self._roll_forward(delta_t)
            self._set_time(now)

    # Set a new time
    def _set_time(self, time):
        self.time = time
        if VERBOSE:
            print 'System time updated to', self.time, '+', \
                self.time - self.start_time

    # Jump forward in time, and transfer data along all active connections
    # at their current rates.
    def _roll_forward(self, delta):
        vms = self.VMs.values()
        for u in vms:
            self.users[u.user][0] += delta

            for v in u.active_transfers.values():
                tp = self._get_link_speed(
                        self._get_group(u), self._get_group(v))

                if u.transfer(v.ip, tp * delta):
                    if u.in_network:
                        self._remove_link(u, v)
