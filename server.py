import random, time, itertools, threading
from collections import defaultdict
from machine import Machine, VirtualMachine
from datacenter import DataCenter

class Server(object):

    def __init__(self, n):
        self.dc = DataCenter()
        self.n = n
        # VMs are indexed by id address
        self.vms = {}
        self.ip_for_vm = {}
