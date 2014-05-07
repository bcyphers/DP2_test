import random, time, itertools, threading
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter
from test import *

dc = DataCenter()
usrs = range(1)  # Just one user to start
n = 50
vms = {u: [] for u in usrs}


# the callback for when a VM completes its job - remove it if it has no more
# data to send or receive.
def on_complete(vm1, vm2id):
    usr = vm1.user
    # since a job involves 2 VMs, check the receiving VM for completion too
    vm2 = next((v for v in vms[usr] if v.ID == vm2id), None)

    for vm in (vm1, vm2):
        # if all of this VM's outgoing transfers are done, see if we can
        # remove it for good
        if len(vm.transfers) == 0:
            # find all this VM's incoming transfers
            it = [[i for i in u.transfers if i == vm.ID] for u in vms[usr]]
            incoming_transfers = list(itertools.chain.from_iterable(it))

            # if there are none left, remove the VM
            if len(incoming_transfers) == 0:
                dc.remove(vm.ID)
                print 'Removing VM with ID', vm.ID
    

# This calculates which (if any) group the VM should jump to
def calc_delta_data(vm):
    while vm.transfers:
        score_by_group = defaultdict(int)
        my_group = int(vm.machine / dc.GROUP_SIZE)

        # Loop over all transfers, and sum up the amount to transfer in
        # each group
        for vid in vm.transfers:
            other_vm = vms[vm.user][v]
            group = int(other_vm.machine / dc.GROUP_SIZE)
            score_by_group[group] += (vm.transfers[vid] + \
                                     other_vm.transfers[vm.ID])

        # Subtract the amount we will lose by leaving the current group
        for g in score_by_group:
            score_by_group[g] -= score_by_group[my_group]

        # Find the max
        vm.max_group_score = max(score_by_group.iteritems(),
                                 key=lambda i: i[1])
        
        # Wait
        time.sleep(1)


# Get the average throughput from any VM to all groups in the system
def average_throughput(vm):
    if vm is None:
        return 0
    tps = [dc.tcp_throughput(vm, u) for u in vms[vm.user] if u is not vm]
    return sum(tps) / len(tps)


def our_strategy():
    # first, place random users around the network with very large connections
    fill_datacenter(dc, 20, 10, 10**7)
    time.sleep(1)  # Wait one second
    
    dc.draw_status()

    # next, place all of our users' VMs around the network greedily
    for u in usrs:
        B = sparse_B(range(u*n, (u+1) * n), 100000, 10)
        for i in range(n):
            vm = VirtualMachine(u, u * n + i, B)
            vm.on_transfer_complete = on_complete  # set callback
            vms[u].append(vm)  # cache the VM here
        
        # sort pairs of VMs by total data to transfer between them
        links = sorted([(v1, v2, v1.to_transfer(v2.ID) + v2.to_transfer(v1.ID))
                        for v1 in vms[u] for v2 in vms[u] if v1 is not v2],
                key=lambda t: -t[2])
        link = links.pop(0)

        group_probes = defaultdict(lambda: None)

        # place the first 24 pairs in the network
        for i in range(dc.NUM_GROUPS):
            if links:
                # If either VM in the link has been placed already,
                # continue to the next link - we want a unique pairing.
                while link[0].ID in dc.VMs or link[1].ID in dc.VMs:
                    link = links.pop(0)
                
                print 'placing link', (link[0].ID, link[1].ID), link[2]

                for m in range(i * dc.GROUP_SIZE,
                               (i + 1) * dc.GROUP_SIZE):
                    if dc.place(link[0], m): 
                        for j in range(i * dc.GROUP_SIZE,
                                       (i + 1) * dc.GROUP_SIZE):
                            # Both links need to be placed
                            if dc.place(link[1], j):
                                group_probes[i] = link[0]
                                break
                        else:
                            # If the second place didn't succeed, remove the
                            # first VM.
                            dc.remove(link[0].ID)
            
        dc.draw_status()
        print 'User', u, ': placing probes complete.'
        time.sleep(1)

        # After that, place the rest of the machines greedily.
        remaining_vms = [v for v in vms[u] if v not in dc.VMs]
        # The optimal group is the one with the highest average throughput.
        optimal_groups = sorted((g for g in range(dc.NUM_GROUPS)),
                key=lambda g: average_throughput(group_probes[g]))

        # loop over the groups in order of highest throughput, and place 
        # as many VMs as possible in each group
        for gr in optimal_groups:
            # The first machine we should try
            m = gr * dc.GROUP_SIZE

            # Track all the VMs in this group
            vms_in_gr = [v for v in vms[u] 
                    if int(v.machine / dc.GROUP_SIZE) == gr]

            # Find the VM with the most data to transfer in the current group
            next_vm = lambda remain: max(remain, key=lambda v1: 
                    sum(v1.to_transfer(v2.ID) + v2.to_transfer(v1.ID) 
                        for v2 in vms_in_gr))

            vm = next_vm(remaining_vms)

            # while there are still VMs left, and we have not tried every
            # machine in the group:
            while remaining_vms and m < (gr + 1) * dc.GROUP_SIZE:
                # try to place the VM
                if dc.place(vm, m):
                    # if successful, remove it from the queue
                    remaining_vms.remove(vm)
                    # recalculate the best option
                    vm = next_vm(remaining_vms)
                else:
                    # if unsuccessful, try the next machine
                    m += 1

            # If there are no more VMs to place, break out of the loop
            if not remaining_vms:
                break

        # Start threads to update the rest of the VMs periodically
        for vm in vms[u]:
            vm.max_group_score = 0
            vthread = threading.Thread(target=calc_delta_data, args=(vm,))
            thread.start()

        dc.draw_status()
        print 'User', u, ': placing all machines complete.'

    # keep updating until everything's finished
    finished = False
    while not finished:
        dc.draw_status()

        finished = True
        for u in usrs:
            for vm in vms[u]:
                # We are finished only when all of our users' VMs are done
                if vm.ID in dc.VMs:
                    finished = False
                    break

            # The next VM we'll try to move is the one with the highest 
            # group score
            vm_to_transfer = max(vms[u], key=lambda v: vm.max_group_score[1])

            if vm_to_transfer.max_group_score[1] > 0:
                # Save the old machine, in case it won't fit in the new group
                old_machine = vm_to_transfer.machine
                dc.remove(vm_to_transfer)

                # the group we want to transfer to, and all the machines in it
                group = vm_to_transfer.max_group_score[0]
                grp_range = range(group * dc.GROUP_SIZE,
                        (group + 1) * dc.GROUP_SIZE)

                # try each one
                for m in grp_range:
                    if dc.place(vm_to_transfer, m):
                        break
                else:
                    # default to the old machine
                    dc.place(vm_to_transfer, old_machine)

        time.sleep(1)

if __name__ == '__main__':
    our_strategy()
