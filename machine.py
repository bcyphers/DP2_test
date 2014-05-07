class VirtualMachine(object):
    # Initialize the VM. B should be a tuple of n tuples of length n, 
    # with B[i][j] referencing the j^th column of the i^th row.
    def __init__(self, user, ID):
        self.machine = None
        self.ip = None
        self.user = user
        self.ID = ID

    def activate(self, B):
        # self.transfers keeps track of all the data which still has to
        # be transferred TO any given VM in the system.
        self.transfers = {vm: B[self][vm] for vm in B 
                if vm != self and B[self][vm] > 0}

        # active_transfers has the vm for all currently running 
        # transfers indexed by IP
        self.active_transfers = {}

        self.total_data = sum(self.transfers.values())

    # Transfer data from self to another VM
    # return True if the transfer terminated, False otherwise
    # If no value for amount is supplied, transfer all data
    def transfer(self, ip, amt=None):
        vm = self.active_transfers[ip]
        if amt == None:
            del self.active_transfers[ip]
            del self.transfers[vm]
            self.on_transfer_complete(self, vm)
            return True
        else:
            self.transfers[vm] -= amt
            if self.transfers[vm] < -100:
                raise Exception('Tried to transfer too much data from' +
                        ' VM ' + str(self.ID) + ' to VM ' + str(vmid) + 
                        '. New amount = ' + str(self.transfers[vm]))
            if self.transfers[vm] < 10 ** -5:
                del self.active_transfers[ip]
                del self.transfers[vm]
                self.on_transfer_complete(self, vm)
                return True

        return False

    # How much data is left to transfer to vm?
    def to_transfer(self, vm):
        try:
            return self.transfers[vm]
        except:
            return 0

    # Begin transferring data to another VM
    def activate_transfer(self, vm, ip):
        self.active_transfers[ip] = vm

    # Callback for whenever a VM transfer completes - should be overridden
    # kinda janky in that you have to pass 'self' as an argument every time
    # - don't know if this is an ok way to do callbacks
    def on_transfer_complete(self, other):
        pass

class Machine(object):
    NUM_VMs = 4
    def __init__(self, ID, VMs=None):
        self.ID = ID
        self.VMs = VMs or []

    # Add a VM to the machine and return it, or return False
    def add_vm(self, VM):
        if len(self.VMs) < self.NUM_VMs:
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
        return self.NUM_VMs - len(self.VMs)
