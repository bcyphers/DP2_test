import random, time, itertools, thread
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter
from test import *

class SmartVM(VirtualMachine):
    
    def __init__(self, user, ID, server):
        super(SmartVM, self).__init__(user, ID)
        self.server = server
        self._group_scores = {i: 0 for i in range(DataCenter.NUM_GROUPS)}
        self.group_scores = self._group_scores.copy()
        self.moved = time.time()

    def sorted_groups(self):
        if self.group() in self.group_scores:
            del self.group_scores[self.group()]
        return sorted(self.group_scores.iteritems(), key=lambda i: -i[1])

    def group(self):
        try:
            return int(self.machine / DataCenter.GROUP_SIZE)
        except:
            return None

    def did_move(self):
        self.moved = time.time()

    def last_moved(self):
        return time.time() - self.moved

    def start_loop(self):
        thread.start_new_thread(self.loop, ())

    def loop(self):
        while True:
            self.calc_group_scores()
            time.sleep(1)

    # This calculates which (if any) group the VM should jump to
    def calc_group_scores(self):
        self._group_scores = {i: 0 for i in range(DataCenter.NUM_GROUPS)}

        # Loop over all transfers, and sum up the amount to transfer in
        # each group
        for vm in self.server.vms:
            group = vm.group()
            if not group:
                continue

            if vm in self.active_transfers.values():
                self._group_scores[group] += self.transfers[vm]

            if self in vm.active_transfers.values():
                self._group_scores[group] += vm.transfers[self]

        if self.machine is not None:
            my_group = self.group()

            # Subtract the amount we will lose by leaving the current group
            for g in self._group_scores:
                self._group_scores[g] -= self._group_scores[my_group]

        # cache our results
        self.group_scores = self._group_scores.copy()

    # Get the average throughput from this VM to all groups in the system
    def average_throughput(self):
        tps = [self.server.dc.tcp_throughput(self, u) for u in vms[self.user] 
                if u is not self]
        return sum(tps) / len(tps)


class Cluster:
    def __init__(self):
        self.vms = []


class SmartServer(Server):

    # Initialize VMs, and start placing them around the network
    def start(self):
        self.vms = [SmartVM(self.user, i, self) for i in range(self.n)]
        self.B = sparse_B(self.vms, self.max_data, 5)
        self.machines_open = {i: [] for i in range(DataCenter.NUM_GROUPS)}
        self.clusters = defaultdict(Cluster)

        for vm in self.vms:
            vm.activate(self.B)
            vm.on_transfer_complete = self.on_complete  # set callback

        self.greedy_place()

    # Greedily place VMs by total data to transfer
    def greedy_place(self):
        self.gather_data()  # update the open machines dict
        vms_to_place = self.vms[:]  # copy VMs into a new list 
        # first_vm = max(self.vms, key=lambda v: sum(v.transfers.values()))
        m = 0

        # try all machines in order
        while vms_to_place:
            v = vms_to_place.pop(0)
            # find the vm with the most connections to the group
            # try to place in the best available spot
            while not self.dc.place(v, m):
                m = (m + 1) % self.dc.NUM_MACHINES 
            
            group = int(m / self.dc.GROUP_SIZE)
            self.clusters[group].vms.append(v)
            v.start_loop()

        self.dc.draw_status()
        self.finished = False

    # keep updating until everything's finished
    def loop(self):
        self.dc.user_time(self.user)
        self.gather_data()

        self.try_move_vm()

        # We are finished when all of our users' VMs are done
        for vm in self.vms:
            if vm.ip in self.dc.VMs:
                break
        else:
            self.finished = True

    def try_move_vm(self):
        # find the best VM to move
        possible_moves = []
        for v in self.vms:
            if v.last_moved() > 10:
                # sorted groups comes with (group, score) tuples
                moves = v.sorted_groups()
                for m in moves:
                    # output is (vm, group, score) tuples
                    if m[1] > 0:
                        possible_moves.append((v, m[0], m[1]))

        possible_moves = sorted(possible_moves, key=lambda m: m[2])

        if possible_moves:
            move = possible_moves.pop()
            if self.machines_open[move[1]]:
                self.move_vm(move[0], self.machines_open[move[1]][0])
            else:
                # get the VM in the current group with the most favorable move
                other_move = next((m for m in possible_moves 
                    if m[1] == move[0].group()), None)
                if other_move:
                    self.swap_vms(move[0], other_move[0])

    # Move a VM from one place to another
    def move_vm(self, vm, machine):
        old_group = int(vm.machine / self.dc.GROUP_SIZE)
        group = int(machine / self.dc.GROUP_SIZE)

        print 'User', self.user, 'Move!', old_group, '->', group

        self.machines_open[old_group].append(vm.machine)
        self.dc.remove(vm.ip)

        if not self.dc.place(vm, machine):
            raise Exception('Something is wrong!')
        
        self.machines_open[group].remove(machine)
        self.clusters[old_group].vms.remove(vm)
        self.clusters[group].vms.append(vm)
        vm.did_move()

    # Swap the positions of two VMs
    def swap_vms(self, vm1, vm2):
        self.dc.pause()

        m1 = vm1.machine
        m2 = vm2.machine
        g1 = int(m1 / self.dc.GROUP_SIZE)
        g2 = int(m2 / self.dc.GROUP_SIZE)

        print 'User', self.user, 'Swap!', g1, '<->', g2

        self.dc.remove(vm1.ip)
        self.dc.remove(vm2.ip)
        self.dc.place(vm1, m2)
        self.dc.place(vm2, m1)

        self.clusters[g1].vms.remove(vm1)
        self.clusters[g2].vms.remove(vm2)
        self.clusters[g2].vms.append(vm1)
        self.clusters[g1].vms.append(vm2)

        vm1.did_move()
        vm2.did_move()

        self.dc.unpause()

    # Move every vm in the cluster from one group to another
    def move_cluster(self, cluster, group):
        self.dc.pause()

        self.clusters[cluster.group] = Cluster()
        for vm in cluster.vms:
            self.dc.remove(vm.ip)
            self.dc.place(vm, self.machines_open[group].pop())
            vm.did_move()
    
        cluster.group = group
        self.clusters[group] = cluster
        
        self.dc.unpause()

    # Find how many slots are open in each group
    def gather_data(self):
        self.dc.pause()
        self.machines_open = {i: [] for i in range(DataCenter.NUM_GROUPS)}

        for m in range(self.dc.NUM_MACHINES):
            group = int(m / self.dc.GROUP_SIZE)
            for x in range(self.dc.machine_occupancy(m)):
                self.machines_open[group].append(m)

        self.dc.unpause()

def simple_test():
    dc = DataCenter()
    
    # initialize everything
    server = SmartServer(0, 100, dc=dc, max_data=100000)
        
    dc.pause()
    server.start()
    dc.unpause()

    # loop through and update every server
    while not server.finished:
        dc.draw_status()
        server.loop()
        time.sleep(1)

def general_test():
    # first, place random users around the network with very large connections
    dc = DataCenter()
    fill_datacenter(dc, 20, 10, 10**7)
    dc.draw_status()
    time.sleep(1)  # Wait one second

    # initialize everything
    servers = [SmartServer(i, 20, dc=dc, max_data=100000) for i in range(10)]

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


# Fill the datacenter with random VMs, assigning them negative ids
def fill_all(dc, num_usr, num_vm, max_data):
    # We want to place one VM in every machine, but in random order.
    machines = range(num_usr * num_vm)
    random.shuffle(machines)

    # the user IDs should iterate over {-1, -2, ..., -num_usr + 1}
    for usr in range(-1, -num_usr, -1):
        # Initialize VMs
        vms = [VirtualMachine(usr, -1) for i in range(num_vm)]
        B = random_B(vms, max_data)

        # activate them and add to the network
        for vm in vms:
            m = machines.pop()
            vm.activate(B)
            vm.on_transfer_complete = lambda v1, v2: None
            dc.place(vm, m)

# WIP
def scenario_1():
    Machine.NUM_VMs = 2
    dc = DataCenter()

    # first, place random users around the network with very large connections
    dc.pause()
    fill_even(dc, 32, 9, 10**7)
    dc.unpause()

    dc.draw_status()
    time.sleep(1)  # Wait one second

    # initialize everything
    servers = [SmartServer(i, 20, dc=dc, max_data=100000) for i in range(10)]

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

# WIPPP
def scenario_2():
    pass

# WIPE
def scenario_3():
    pass

if __name__ == '__main__':
    general_test()
