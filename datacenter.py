import sys, math, random, time
from machine import Machine, VirtualMachine

class DataCenter(object):
    NUM_MACHINES = 1152
    GROUP_SIZE = 48
    NUM_GROUPS = 24
    AGG_ROUTERS = 4
    THROUGHPUT = 10000.0  # in MBPS

    def __init__(self):
        # machines stores Machine objects indexed by machine_id
        self.machines = {i: Machine(i) for i in xrange(self.NUM_MACHINES)}

        # groups stores collections of machines indexed by group id
        self.groups = {i: [self.machines[j] for j in xrange(
            i * self.GROUP_SIZE, (i + 1) * self.GROUP_SIZE)] 
            for i in xrange(self.NUM_GROUPS)}

        # Links are represented as tuples: (lower level, upper level)
        # each link points to a list of the connections it currently serves.
        # For our purposes, the redundant routers are lumped into one.
        self.agg_links = {link: set() for link in 
                    [(i, int(i/6)) for i in range(self.NUM_GROUPS)]}
        self.core_links = {link: set() for link in range(self.AGG_ROUTERS)}

        # VMs stores VM objects indexed by their private IP address
        self.VMs = {}

        # this is the last time the system was updated
        self.time = time.time()

        print 'Data center initialized.'
    
    # Place VM v on machine m, or return False if it is full
    def place(self, v, m):
        self._tick()
        if m not in self.machines:
            raise Exception('Not a valid machine ID')
        if self.machines[m].add_vm(v):
            ip = self.get_new_ip()
            self.VMs[ip] = v
            v.machine = m
            print 'Added VM with ip', ip, 'to machine', m
            return ip
        print 'Tried to add to machine ' + str(m) + ', which is full'
        return False

    # Place VM v on a random machine. Return the machine's id and the VM's ip
    # if successful, or raise an error if the entire datacenter is full.
    def random_place(self, v):
        self._tick()
        machines_tried = set()
        
        # try machines at random until every one has been tried
        while len(machines_tried) < self.:
            m = random.randrange(self.NUM_MACHINES)
            machines_tried.add(m)

            # if space is available in m, place v there
            if self.machine_occupancy(m) > 0:
                print 'Placing VM at random machine, id =', m
                return m, self.place(v, m)

        # we have tried everything, so the datacenter is full
        raise Exception('No machines available')

    # Return the number of bytes left to transfer between u and v
    # TODO: find out what this actually means
    def progress(self, u, v):
        self._tick()
        return u.to_transfer(v.ID) + v.to_transfer(u.ID)

    # Return the number of VMs on machine m
    def machine_occupancy(self, m):
        self._tick()
        return self.machines[m].occupancy()

    # Returns the throughput of the TCP connection from u -> v over
    # the last 100ms
    # TODO: figure out how
    def tcp_throughput(self, u, v):
        pass

    # Get a random, unused ip for a VM
    def _get_rand_ip(self):
        rand_ip = lambda: '.'.join([str(random.randrange(256)) 
                                    for i in range(4)])
        ip = rand_ip()
        while ip in self.VMs:  # try until we find one we haven't used
            ip = rand_ip()
        return ip


    '''
    TODO: Below here everything is unfinished!!@!@!
    '''

    # Add a link between two machines
    def _add_link(self, vm1, vm2):
        m1 = vm1.machine
        m2 = vm2.machine
        g1 = int(m1 / self.GROUP_SIZE)
        g2 = int(m2 / self.GROUP_SIZE)
        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # Add the vm connection to the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].add((vm1.ID, vm2.ID)) 
        self.agg_links[(g2, ag2)].add((vm1.ID, vm2.ID)) 

        # Add the connection to the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].add((vm1.ID, vm2.ID))
            self.core_links[ag2].add((vm1.ID, vm2.ID))


    # Delete a link between two machines
    def _remove_link(self, vm1, vm2):
        m1 = vm1.machine
        m2 = vm2.machine
        g1 = int(m1 / self.GROUP_SIZE)
        g2 = int(m2 / self.GROUP_SIZE)
        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # remove the connection from the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].remove((vm1.ID, vm2.ID)) 
        self.agg_links[(g2, ag2)].remove((vm1.ID, vm2.ID)) 

        # remove the connection from the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].remove((vm1.ID, vm2.ID))
            self.core_links[ag2].remove((vm1.ID, vm2.ID))

    # What is the throughput (in MBPS) between two groups?
    # This assumes that all connections are given equal speeds
    def _get_link_speed(self, g1, g2):
        if g1 == g2:
            return self.THROUGHPUT

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # hacky 1-liner
        links = [self.agg_links[(g1, ag1)],
                self.agg_links[(g2, ag2)]] +\
                [self.core_links[ag1], self.core_links[ag2]] \
                if ag1 != ag2 else []

        # the highest number of connections on any of the links between g1 & g2
        max_connects = max(len(link) for link in links)

        # we can't actually have throughput greater than 10 mbps
        return 2 * self.THROUGHPUT / max(max_connects, 2)

    def _get_group(self, vm):
        return int(vm.machine / self.GROUP_SIZE)

    # Update the state of the data center
    def _tick(self):
        delta_t = time.time() - self.time
        self.time = time.time()
        
        for u in self.VMs.iteritems():
            throughput = self._get_link_speed(self._get_group(vm) )
