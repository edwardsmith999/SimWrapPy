from simwraplib.inpututils import ScriptMod 
from simwraplib.run import Run

class ScriptRun(Run):

    def __init__(self,
                 rundir,
                 executable,
                 inputchanges={},
                 dryrun=False
                ):

        #Inherit constructor from base class
        # Script itself is the input file
        super(ScriptRun, self).__init__(rundir=rundir, 
                                        executable=executable,
                                        inputfile=executable,
                                        inputchanges=inputchanges,
                                        dryrun=dryrun)

        # Set input modifier to be normal kind
        self.inputmod = ScriptMod

    def prepare_cmd_arguments(self, fdir=''):
        self.cmd_args = ''
        return self.cmd_args

    def get_nprocs(self, *args, **kwargs):         
        return 1 

    def finish(self):
        pass

