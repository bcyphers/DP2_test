import random, time, itertools
from machine import Machine, VirtualMachine
from datacenter import DataCenter

# This is some filler test code. It creates 20 VMs with a random B matrix,
# and randomly places them in the data center one-by-one, with a half second
# delay in between. No logic at all, just tests the system.
if __name__ == '__main__':
    dc = DataCenter()
    usr = 0  # this test just uses one user, but we could add more
    n = 20  # the total number of VMs
    vms = []  # hold our VMs for easy access

    # generate B as a tuple of tuples, n x n
    B = tuple(tuple(random.randrange(10000) 
                    if i != j else 0 for j in range(n)) 
              for i in range(n))

    # the callback for when the VMs complete their jobs - removes them if done
    def on_complete(vm1, vm2id):

        # since a job involves 2 VMs, check the receiving VM for completion too
        vm2 = next((v for v in vms if v.ID == vm2id), None)

        for vm in (vm1, vm2):
            # if all of this VM's outgoing transfers are done, see if we can
            # remove it for good
            if len(vm.transfers) == 0:
                # find all this VM's incoming transfers
                it = [[i for i in u.transfers if i == vm.ID] for u in vms]
                incoming_transfers = list(itertools.chain.from_iterable(it))

                # if there are none left, remove the VM
                if len(incoming_transfers) == 0:
                    dc.remove(vm.ID)
                    print 'Removing VM with ID', vm.ID
    
    # start by placing all the VMs randomly around the network
    for i in range(n):
        vm = VirtualMachine(usr, i, B)
        vm.on_transfer_complete = on_complete  # set callback
        vms.append(vm)  # cache the VM here
        dc.random_place(vm)  # place!
        dc.draw_status()
        time.sleep(0.5)  # aand wait

    # keep updating until everything's finished
    while dc.VMs:
        dc.draw_status()
        time.sleep(1)
