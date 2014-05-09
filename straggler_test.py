import random, time, itertools, thread
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter
from test import *

#Straw man three
class StragglerServer(Server):
    # Initialize VMs, and start placing them around the network.
    # When finished, transition to loop.
    def start(self):
        # a random matrix with 20 VMs, exchanging 10 GB max
        self.vms = [VirtualMachine(self.user, i) for i in range(self.n)]
        #print self.vms
        #print self.n
        self.B = sparse_B(self.vms, self.max_data, 5)
        self.finished = False

        # Store initial amount of data to transfer for convenience
        self.starting_progress = {}
        for i in range(len(self.vms)):
            for j in range(i+1, len(self.vms)):
                vm1 = self.vms[i]
                vm2 = self.vms[j]
                self.starting_progress[(i, j)] = self.B[vm1][vm2] + self.B[vm2][vm1]

        # start by placing all the VMs randomly around the network
        for vm in self.vms:
            vm.activate(self.B)
            vm.on_transfer_complete = self.on_complete  # set callback
            self.dc.random_place(vm)

        self.dc.draw_status()

    def loop(self):
        self.finished = True
        for vm in self.vms:
            if vm.ip in self.dc.VMs:
                self.finished = False

        
        # Collect progress between all pairs
        # Find lowest amount of progress
        min_progress = 150
        min_progress_pair = ()
        if not self.finished:
            for i in range(len(self.vms)):
                for j in range(i+1, len(self.vms)):
                    #print j
                    vm1 = self.vms[i]
                    try:
                        vm2 = self.vms[j]
                    except IndexError, e:
                        continue
                    progress = self.dc.progress(vm1, vm2)
                    percent = 0
                    # for now assumes that VMs making zero progress have finished
                    if self.starting_progress[(i, j)] != 0:
                        # Progress = amount of data transferred / amount to transfer overall
                        percent = int(100 * (self.starting_progress[(i, j)] - progress) / self.starting_progress[(i, j)])
                    if percent != 0:
                        min_progress = min(percent, min_progress)
                        min_progress_pair = (vm1, vm2)

            # Get the pair making the least amount of progress and randomly move one of the VMs somewhere else
            try:
                vm_to_move = min_progress_pair[random.randint(0, 1)]
                self.dc.remove(vm_to_move.ip)
                self.dc.random_place(vm_to_move)
            except Exception, e: #find out why this is happening
                pass 
            #self.dc.draw_status()
            #time.sleep(1)

def simple_test():
    dc = DataCenter()
    
    # initialize everything
    server = StragglerServer(0, 20, dc=dc, max_data=10000)
        
    dc.pause()
    server.start()
    dc.unpause()

    # loop through and update every server
    while not server.finished:
        dc.draw_status()
        server.loop()
        time.sleep(1)

def straggler_test():
    # first, place random users around the network with very large connections
    dc = DataCenter()
    fill_datacenter(dc, 20, 10, 10**4)
    dc.draw_status()
    time.sleep(1)  # Wait one second

    # initialize everything
    servers = [StragglerServer(i, 10, dc=dc, max_data=10000) for i in range(5)]

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

if __name__ == '__main__':
    #simple_test()
    straggler_test()
