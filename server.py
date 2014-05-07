import random, time, itertools, threading
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter

class ModifiedVM(VirtualMachine):
    
    def __init__(self, user, ID, server):
        super(ModifiedVM, self).__init__(user, ID)
        self.server = server
        self.group_scores = {i: 0 for i in range(DataCenter.NUM_GROUPS)}

    def best_group(self):
        return max(self.group_scores, key=lambda g: self.group_scores[g])

    # This calculates which (if any) group the VM should jump to
    def calc_group_scores(self):
        my_group = int(self.machine / DataCenter.GROUP_SIZE)

        # Loop over all transfers, and sum up the amount to transfer in
        # each group
        for vm, amount in self.transfers.iteritems():
            group = int(vm.machine / DataCenter.GROUP_SIZE)
            self.group_scores[group] += (amount + vm.transfers[self])

        # Subtract the amount we will lose by leaving the current group
        for g in group_scores:
            group_scores[g] -= group_scores[my_group]

        # Wait
        time.sleep(1)

    # Get the average throughput from this VM to all groups in the system
    def average_throughput(self):
        tps = [dc.tcp_throughput(self, u) for u in vms[self.user] 
                if u is not self]
        return sum(tps) / len(tps)


class Server(object):

    def __init__(self, user, n):
        self.dc = DataCenter()
        self.n = n
        self.user = user
        self.vms = {}

    def start(self):
        # les do it
        pass

    def greedy_place(self):
        # place all VMs as close as possible
        pass

    def loop(self):
        # keep reassigning VMs til they done
        pass

    def move_vm(self, vm, machine):
        # yup
        pass

    def swap_vms(self, vm1, vm2):
        # yep
        pass

    def move_cluster(self, cluster, group):
        # mmm hmm
        pass

    def gather_data(self):
        # Find how many slots are open in each group
        pass

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
                    self.dc.remove(vm.ip)
                    print 'Removing VM with ID', vm.ID
        
