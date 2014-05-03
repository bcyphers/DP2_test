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

        # VMs stores VM objects indexed by ID
        self.VMs = {}
        # self-explanatory, indexed by IP address
        self.vm_by_ip = {}

        # this is the last time the system was updated
        self.time = time.time()
        self.start_time = self.time

        print 'Data center initialized.'
    
    # Place VM v on machine m, or return False if it is full
    def place(self, v, m):
        self._update()
        if m not in self.machines:
            raise Exception('Not a valid machine ID')

        if self.machines[m].add_vm(v):
            ip = self._get_rand_ip()
            self.vm_by_ip[ip] = v
            self.VMs[v.ID] = v
            v.machine = m
            
            # add a link for each one of this VM's connections in the system
            for target in v.transfers.iterkeys():
                if target in self.VMs:
                    self._add_link(v, self.VMs[target])
                    v.activate_transfer(target, ip)

            # check to see if other VMs in the system link to the new one
            for u in self.VMs.values():
                if v.ID in u.transfers.iterkeys():
                    self._add_link(u, v)
                    u.activate_transfer(v.ID, ip)

            print 'Added VM with ip', ip, 'to machine', m
            return ip

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

        print 'Placing VM at random machine, id =', m
        return m, self.place(v, m)

    # Return the number of bytes left to transfer between u and v
    # TODO: find out what this actually means
    def progress(self, u, v):
        self._update()
        return u.to_transfer(v.ID) + v.to_transfer(u.ID)

    # Return the number of VMs on machine m
    def machine_occupancy(self, m):
        self._update()
        return self.machines[m].occupancy()

    # Returns the throughput of the TCP connection from u -> v over
    # the last 100ms
    # TODO: figure out how - this gets the current link speed; not the same
    def tcp_throughput(self, u, v):
        return self._get_link_speed(self._get_group(u), self._get_group(v))

    # Get a random, unused ip for a VM
    def _get_rand_ip(self):
        rand_ip = lambda: '.'.join([str(random.randrange(256)) 
                                    for i in range(4)])
        ip = rand_ip()
        while ip in self.vm_by_ip:  # try until we find one we haven't used
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
        if g1 == g2:  # Don't add anything if they're in the same group
            return

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # Add the vm connection to the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].add((vm1.ID, vm2.ID)) 
        self.agg_links[(g2, ag2)].add((vm1.ID, vm2.ID)) 

        # Add the connection to the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].add((vm1.ID, vm2.ID))
            self.core_links[ag2].add((vm1.ID, vm2.ID))

        print 'Added link from VM', vm1.ID, 'to VM', vm2.ID


    # Delete a link between two machines
    def _remove_link(self, vm1, vm2):
        m1 = vm1.machine
        m2 = vm2.machine
        g1 = self._get_group(vm1)
        g2 = self._get_group(vm2)
        if g1 == g2:
            return

        ag1 = int(g1 / 6)
        ag2 = int(g2 / 6)

        # remove the connection from the (group -> aggregate group) links
        self.agg_links[(g1, ag1)].remove((vm1.ID, vm2.ID)) 
        self.agg_links[(g2, ag2)].remove((vm1.ID, vm2.ID)) 

        # remove the connection from the (aggregate -> core) links
        if ag1 != ag2:
            self.core_links[ag1].remove((vm1.ID, vm2.ID))
            self.core_links[ag2].remove((vm1.ID, vm2.ID))

        print 'Removed link from VM', vm1.ID, 'to VM', vm2.ID

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
        try:
            max_connects = max(len(link) for link in links)
        except ValueError as v:
            # debugging code: this keeps throwing errors for some reason
            print v
            print sorted(self.agg_links.iteritems())
            print sorted(self.core_links.iteritems())
            print g1, g2

        # we can't actually have throughput greater than 10 mbps
        return 2 * self.THROUGHPUT / max(max_connects, 2)

    # Update the state of the data center
    def _update(self):
        delta_t = time.time() - self.time
        mttc = float('inf')  # min time to completion
        
        for u in self.VMs.itervalues():
            for vid in u.active_transfers.iterkeys():
                amt = u.transfers[vid]
                v = self.VMs[vid]
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
            self._set_time(time.time())

    # Set a new time
    def _set_time(self, time):
        self.time = time
        print 'System time updated to', self.time, '+', \
                self.time - self.start_time

    # Jump forward in time, and transfer data along all active connections
    # at their current rates.
    def _roll_forward(self, delta):
        for u in self.VMs.itervalues():
            for vid in u.active_transfers.keys():
                v = self.VMs[vid]
                tp = self._get_link_speed(
                        self._get_group(u), self._get_group(v))
                if u.transfer(vid, tp * delta):
                    self._remove_link(u, v)

# This is some simple test code. It creates 100 VMs with a random B matrix,
# and randomly places them in the data center one-by-one, with a 1 second
# delay in between.
if __name__ == '__main__':
    dc = DataCenter()
    B = tuple(tuple(random.randrange(1000) * 10 ** random.randrange(3) 
                    if i != j else 0 for j in range(100)) 
              for i in range(100))

    for i in range(100):
        vm = VirtualMachine(i, B)
        dc.random_place(vm)
        time.sleep(1)
