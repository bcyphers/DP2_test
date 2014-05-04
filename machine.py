class VirtualMachine(object):
    # Initialize the VM. B should be a tuple of n tuples of length n, 
    # with B[i][j] referencing the j^th column of the i^th row.
    def __init__(self, user, ID, B):
        self.machine = None
        self.ip = None
        self.user = user
        self.ID = ID

        # self.transfers keeps track of all the data which still has to
        # be transferred TO any given VM in the system.
        self.transfers = {i: B[ID][i] for i in B if i != ID and B[ID][i] > 0}

        # active_transfers has the ip addressed for all currently running 
        # transfers indexed by VMID
        self.active_transfers = {}

    # Transfer data from self to another VM
    # return True if the transfer terminated, False otherwise
    # If no value for amount is supplied, transfer all data
    def transfer(self, vmid, amt=None):
        if amt == None:
            del self.transfers[vmid]
            del self.active_transfers[vmid]
            # print 'VM', self.ID,'- connection to', vmid, 'finished!'
            self.on_transfer_complete(self, vmid)
            return True
        else:
            self.transfers[vmid] -= amt
            if self.transfers[vmid] < -100:
                raise Exception('Tried to transfer too much data from' +
                        ' VM ' + str(self.ID) + ' to VM ' + str(vmid) + 
                        '. New amount = ' + str(self.transfers[vmid]))
            if self.transfers[vmid] < 10 ** -5:
                del self.transfers[vmid]
                del self.active_transfers[vmid]
                # print 'VM', self.ID,'- connection to', vmid, 'finished!'
                self.on_transfer_complete(self, vmid)
                return True

        return False

    # How much data is left to transfer to vmid?
    def to_transfer(self, vmid):
        return self.transfers[vmid]

    # Begin transferring data to another VM
    def activate_transfer(self, vmid, ip):
        self.active_transfers[vmid] = ip

    # Callback for whenever a VM transfer completes - should be overridden
    # kinda janky in that you have to pass 'self' as an argument every time
    # - don't know if this is an ok way to do callbacks
    def on_transfer_complete(self, other):
        pass

class Machine(object):
    def __init__(self, ID, VMs=None):
        self.ID = ID
        self.VMs = VMs or []

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
