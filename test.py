import random, time, itertools, threading
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter

# generate B as a dict of dicts, n x n, with random amounts of data up to 
# max_data megabytes to transfer. vmids is a list of ID numbers, not an int
# B is guaranteed to be a full matrix, although it may contain zeroes.
def random_B(vms, max_data):
    return {u: {v: random.randrange(max_data) 
                    if u is not v else 0 for v in vms} 
              for u in vms}

# generate a B matrix with at most max_conn connections from any given VM. 
def sparse_B(vms, max_data, max_conn):
    B = {}
    for u in vms:
        # Randomly choose max_conn VMs from the set to connect to
        out_connections = random.sample(vms, max_conn)
        B[u] = {}

        for v in vms:
            if v is not u and v in out_connections:
                B[u][v] = random.randrange(max_data) 
            else:
                B[u][v] = 0

    return B

# Fill the datacenter with random VMs, assigning them negative ids
def fill_datacenter(dc, num_usr, num_vm, max_data):
    # the user IDs should iterate over {-1, -2, ..., -num_usr + 1}
    for usr in range(-1, -num_usr, -1):
        # Initialize VMs
        vms = [VirtualMachine(usr, -1) for i in range(num_vm)]
        B = random_B(vms, max_data)

        # activate them and add to the network
        for vm in vms:
            vm.activate(B)
            vm.on_transfer_complete = lambda v1, v2: None
            dc.random_place(vm)

# A class representing the remote API server, which handles placement logic
class Server(object):

    def __init__(self, user, n, dc=None, max_data=10000):
        self.dc = dc or DataCenter()
        self.n = n
        self.user = user
        self.vms = []
        self.max_data = max_data

    # Initialize VMs, and start placing them around the network.
    # When finished, transition to loop.
    def start(self):
        # a random matrix with 20 VMs, exchanging 10 GB max
        self.vms = [VirtualMachine(self.user, i) for i in range(self.n)]
        self.B = random_B(self.vms, self.max_data)  

        # start by placing all the VMs randomly around the network
        for vm in self.vms:
            vm.activate(self.B)
            vm.on_transfer_complete = self.on_complete  # set callback
            self.dc.random_place(vm)  # place!
            self.dc.draw_status()
            time.sleep(0.5)  # aand wait

    def loop(self):
        # keep updating until everything's finished
        while self.dc.VMs:
            self.dc.draw_status()
            time.sleep(1)

    # the callback for when a VM completes its job - remove it if it has no
    # more data to send or receive.
    def on_complete(self, vm1, vm2):
        for vm in (vm1, vm2):
            # if all of this VM's outgoing transfers are done, see if we can
            # remove it for good
            if len(vm.transfers) == 0:
                # find all this VM's incoming transfers
                for v in self.vms:
                    if vm in v.transfers:
                        break
                else:
                    # if there are none left, remove the VM
                    vm.in_network = False 
                    self.vms.remove(vm)
        
if __name__ == '__main__':
    server = Server(0, 20)
    server.start()
    server.loop()
