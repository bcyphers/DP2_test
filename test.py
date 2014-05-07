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
            if u is not v and u in out_connections:
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

# This is some filler test code. It creates 20 VMs with a random B matrix,
# and randomly places them in the data center one-by-one, with a half second
# delay in between. No logic at all, just tests the system.
def dumb_test():
    dc = DataCenter()
    usr = 0  # this test just uses one user, but we could add more
    vms = []  # hold our VMs for easy access
    n = 20

    # a random matrix with 20 VMs, exchanging 10 GB max
    B = random_B(range(n), 10000)  

    # the callback for when a VM completes its job - remove it if it has no more
    # data to send or receive.
    def on_complete(vm1, vm2):
        for vm in (vm1, vm2):
            # if all of this VM's outgoing transfers are done, see if we can
            # remove it for good
            if len(vm.transfers) == 0:
                # find all this VM's incoming transfers
                for v in vms:
                    if vm in v.transfers:
                        break
                else:
                    # if there are none left, remove the VM
                    dc.remove(vm.ip)
                    print 'Removing VM with ID', vm.ID

    # start by placing all the VMs randomly around the network
    for i in range(n):
        vm = VirtualMachine(usr, i)
        vm.activate(B)
        vm.on_transfer_complete = on_complete  # set callback
        vms.append(vm)  # cache the VM here
        dc.random_place(vm)  # place!
        dc.draw_status()
        time.sleep(0.5)  # aand wait

    # keep updating until everything's finished
    while dc.VMs:
        dc.draw_status()
        time.sleep(1)

def greedy_place():
    dc = DataCenter()
    usrs = range(10)
    n = 20
    vms = {u: [] for u in usrs}

    # the callback for when a VM completes its job - remove it if it has no more
    # data to send or receive.
    def on_complete(vm1, vm2):
        usr = vm1.user
        for vm in (vm1, vm2):
            # if all of this VM's outgoing transfers are done, see if we can
            # remove it for good
            if len(vm.transfers) == 0:
                # find all this VM's incoming transfers
                for v in vms[usr]:
                    if vm in v.transfers:
                        break
                else:
                    # if there are none left, remove the VM
                    dc.remove(vm.ip)
        
    # first, place random users around the network with very large connections
    fill_datacenter(dc, 20, 10, 10**7)
    time.sleep(1)  # Wait one second
    
    dc.draw_status()

    # next, place all of our users' VMs around the network greedily
    for u in usrs:
        vms[u] = [VirtualMachine(u, i) for i in range(n)]
        B = sparse_B(vms[u], 400000, 5)

        for vm in vms[u]:
            vm.activate(B)
            vm.on_transfer_complete = on_complete  # set callback
        
        # sort the VMs by total data to transfer
        sorted_vms = sorted(vms[u], key=lambda v: -sum(v.transfers.values()))

        # try all machines in order
        m = 0
        for v in sorted_vms:
            # try to place in the first available spot
            while not dc.place(v, m):
                m = (m + 1) % dc.NUM_MACHINES            

        dc.draw_status()

    # keep updating until everything's finished
    finished = False
    while not finished:
        dc.draw_status()
        time.sleep(1)

        # We are finished when all of our users' VMs are done
        finished = True
        for u in usrs:
            for vm in vms[u]:
                if vm.ip in dc.VMs:
                    finished = False
                    break


if __name__ == '__main__':
    greedy_place()
