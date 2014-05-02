class VirtualMachine(object):
    # Initialize the VM. B should be a tuple of n tuples of length n, 
    # with B[i][j] referencing the j^th column of the i^th row.
    def __init__(self, ID, B):
        self.machine = None
        self.ID = ID

        # self.transfers keeps track of all the data which still has to
        # be transferred TO any given VM in the system.
        self.transfers = {i: B[ID][i] for i in range(len(B))}

    # Transfer data from self to another VM
    def transfer(self, vmid, amt=None):
        if amt == None:
            self.transfers[vmid] = 0
        else:
            self.transfers[vmid] -= amt

    # How much data is left to transfer to vmid?
    def to_transfer(self, vmid):
        return self.transfers[vmid]


class Machine(object):
    def __init__(self, ID, VMs=[]):
        self.ID = id_num
        self.VMs = VMs

    # Add a VM to the machine and return it, or return False
    def add_vm(self, VM):
        if len(self.VMs) < 4:
            self.VMs.append(VM)
            return VM
        else:
            return False

    # Remove a VM from the machine, or return False if it wasn't in here
    def remove_vm(self, VM):
        if VM in self.VMs:
            self.VMs.remove(VM)
            return True
        else:
            return False

    # How many open slots does this machine have?
    def occupancy(self):
        return 4 - len(self.VMs)
