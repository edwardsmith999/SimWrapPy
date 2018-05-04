import os
import shutil as sh
import subprocess as sp
import shlex

from simwraplib.platform import get_platform
from simwraplib.hpc import PBSJob
from simwraplib.inpututils import MDInputMod 
from simwraplib.run import Run

class MinimalRun(Run):

    def __init__(self,
                 srcdir=None,
                 basedir=None,
                 rundir=None,
                 executable='./a.out',
                 inputfile='inputfile',
                 inputchanges={},
                 dryrun=False
                ):

        #Inherit constructor from base class
        super(MinimalRun, self).__init__(srcdir=srcdir, 
                                         basedir=basedir, 
                                         rundir=rundir, 
                                         executable=executable,
                                         inputfile=inputfile,
                                         inputchanges=inputchanges,
                                         dryrun=dryrun)

        # Set input modifier to be normal kind
        self.inputmod = MDInputMod

    def prepare_cmd_arguments(self, fdir=''):
        self.cmd_args = ''
        return self.cmd_args

    def get_nprocs(self, *args, **kwargs):         
        return 1 

    def finish(self):
        pass

