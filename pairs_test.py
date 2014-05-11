import random, time, itertools, thread
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter
from test import *

class PairwiseServer(Server):
    # Place all of our users' VMs around the network greedily
    def start(self):
        self.vms = [VirtualMachine(self.user, i) for i in range(self.n)]
        self.B = sparse_B(self.vms, self.max_data, 5)

        for vm in self.vms:
            vm.activate(self.B)
            vm.on_transfer_complete = self.on_complete  # set callback
        
        # sort the VMs by total data to transfer
        sorted_vms = sorted(self.vms, key=lambda v: -sum(v.transfers.values()))

        # try all machines in order
        m = 0
        for v in sorted_vms:
            # try to place in the first available spot
            while not self.dc.place(v, m):
                m = (m + 1) % self.dc.NUM_MACHINES            

        self.dc.draw_status()
        self.finished = False

    # keep updating until everything's finished
    def loop(self):
        self.dc.user_time(self.user)

        # We are finished when all of our users' VMs are done
        self.finished = True
        for vm in self.vms:
            if vm.ip in dc.VMs:
                self.finished = False

        if self.finished or not self.vms:
            return

        # choose a random pair
        vm1 = random.choice(self.vms)
        choices = [v for v in vm1.transfers if v in self.vms]
        if choices:
            vm2 = random.choice(choices)
        else:
            return

        # find machine
        self.dc.pause()
        machines = [m for m in range(DataCenter.NUM_MACHINES) 
                if self.dc.machine_occupancy(m) >= 2]
        self.dc.unpause()

        m = random.choice(machines)

        # remove from old machines
        if vm1.ip in self.dc.VMs:
            self.dc.remove(vm1.ip)
        if vm2.ip in self.dc.VMs:
            self.dc.remove(vm2.ip)

        # place
        self.dc.place(vm1, m)
        self.dc.place(vm2, m)


if __name__ == '__main__':
    # first, place random users around the network with very large connections
    dc = DataCenter()
    fill_datacenter(dc, 20, 10, 10**7)
    dc.draw_status()
    time.sleep(1)  # Wait one second

    # initialize everything
    servers = [PairwiseServer(i, 20, dc=dc, max_data=100000) for i in range(10)]

    dc.pause()
    for server in servers:
        server.start()
    dc.unpause()

    # loop through and update every server
    while len([s for s in servers if not s.finished]):
        dc.draw_status()
        for s in servers:
            if not s.finished:
                s.loop()
        time.sleep(1)
