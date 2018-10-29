import numpy as np

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
        #Have a look in python file for standard processor format
        found = False
        try:
            if ".py" in self.executable:
                with open(self.executable, 'r') as f:
                    for l in f:
                        print(l)
                        if "npxyz =" in l:
                            npxyz = [int(i) for i in l.split("=")[1]
                                                      .replace("[","")
                                                      .replace("]","")
                                                      .replace("np.array","")
                                                      .replace("(","")
                                                      .replace(")","")
                                                      .replace("\n","")
                                                      .split(",")]
                            found = True
                            break
                if found:
                    return np.product(npxyz)
        except ValueError:
            print("Warning in get_nprocs - Cannot work out processor number")

        return 1            

    def finish(self):
        pass

