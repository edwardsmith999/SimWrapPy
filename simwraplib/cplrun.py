import shlex
import os
import shutil as sh
import subprocess as sp

from simwraplib.scriptrun import ScriptRun
from simwraplib.run import Run
from simwraplib.inpututils import InputMod
from simwraplib.platform import get_platform
from simwraplib.hpc import PBSJob
from simwraplib.lammpsrun import LammpsRun
from simwraplib.openfoamrun import OpenFOAMRun
from simwraplib.mdrun import MDRun

#This is the run string needed if
#cannot run directly
runfilestr = """
#!/usr/bin/env python

import subprocess as sp

def get_subprocess_error(e):
    print("subprocess ERROR")
    import json
    error = json.loads(e[7:])
    print(error['code'], error['message'])

try:
    run=sp.check_output(RUNCMDHERE, shell=True)
    print(run)
except sp.CalledProcessError as e:
    if e.output.startswith('error: {'):
        get_subprocess_error(e.output)
    raise
"""

class CPLRun(Run):
    
    def __init__(self, 
                 srcdir='../src/',
                 basedir='../',
                 rundir='../runs/',
                 executable=None,
                 inputfile='COUPLER.in',
                 outputfile='COUPLER.out',
                 inputchanges={},
                 initstate=None,
                 restartfile=None,
                 jobname='cpl_job',
                 walltime='00:09:00',
                 extraargs={},
                 queue='',
                 platform=None,
                 extrafiles=None, 
                 finishargs={},
                 dryrun=False,
                 deleteoutput=False
                ):

        assert type(executable) is list
        assert len(executable) is 2

        #This will need to be generalised to an MD/CFD run baseclass
        assert (type(executable[0]) is LammpsRun or 
                type(executable[0]) is MDRun or 
                type(executable[0]) is ScriptRun)
        assert (type(executable[1]) is OpenFOAMRun or 
                type(executable[1]) is ScriptRun)

        self.mdrun = executable[0]
        self.cfdrun = executable[1]

        #Inherit constructor from base class
        super(CPLRun, self).__init__(srcdir=srcdir, 
                                     basedir=basedir, 
                                     rundir=rundir, 
                                     executable=executable,
                                     inputfile=inputfile, 
                                     outputfile=outputfile, 
                                     inputchanges=inputchanges,
                                     initstate=initstate, 
                                     restartfile=restartfile, 
                                     jobname=jobname, walltime=walltime, 
                                     extraargs=extraargs, queue=queue, 
                                     platform=platform,
                                     extrafiles=extrafiles, 
                                     finishargs=finishargs, 
                                     dryrun=dryrun,
                                     deleteoutput=deleteoutput)

        if (self.basedir == None):
            if (self.mdrun.basedir == self.cfdrun.basedir):
                self.basedir = self.mdrun.basedir
            else:
                quit('Unable to obtain base directory for coupler inputs')

        # Set input modifier to be normal kind
        self.inputmod = InputMod

    def build_executable(self, debug=False, platform="intel"):

        """
           Trigger a (re)build of CPL library from
           the source code directory
                
        """

        print("Attempting to build code from executable")
        print("Note that this is not really the responsisbility")
        print("of simwraplib which expects the user to have done this")

        #First try make
        try:
            cmdstg = 'make'
  
            #Call build and wait until build has finished 
            #before returning control to caller
            split_cmdstg = shlex.split(cmdstg)
            self.build = sp.Popen(split_cmdstg, cwd=self.srcdir)
            self.build.wait()

        except:
            print("Build Failed, try building manually before running simwraplib")
            raise

        return

    def setup(self):

        # Create dir and copy coupler input file
        super(CPLRun, self).setup()

        self.create_rundir()
        self.copyfile(self.inputfile)

        # Enforce directory structure for now
        self.mdrunsubdir = './md_data/'
        self.cfdrunsubdir = './cfd_data/'
        print('Resetting MDRun rundir to ' + self.rundir + self.mdrunsubdir)
        print('Resetting CFDRun rundir to ' + self.rundir + self.cfdrunsubdir)
        self.mdrun.rundir = self.rundir + self.mdrunsubdir
        self.cfdrun.rundir = self.rundir + self.cfdrunsubdir

        self.prepare_inputs()
        #Call MD and CFD setup to prepare each input as needed
        self.mdrun.setup()
        self.cfdrun.setup()

    def get_nprocs(self):
        self.mdprocs = self.mdrun.get_nprocs()
        self.cfdprocs = self.cfdrun.get_nprocs()
        return self.mdprocs + self.cfdprocs

    def prepare_mpiexec(self):

        # cplexec wrapper is the easiest way to run but
        # will not work on some supercomputer platforms

        if (self.platform == 'archer'):
            mpiexec = 'aprun'
        elif ("cx1" in self.platform):
            mpiexec = 'mpiexec hetrostart'
        elif ("cx2" in self.platform):
            mpiexec = 'mpiexec'
        elif (self.platform == 'local'):
            mpiexec = 'cplexec'

        return mpiexec

    def prepare_cmd_string(self, executable, nprocs, extra_cmds=""):

        assert nprocs == self.mdprocs + self.cfdprocs
        self.mpiexec = self.prepare_mpiexec()
        self.mdexec = self.mdrunsubdir + self.mdrun.executable
        self.cfdexec = self.cfdrunsubdir + self.cfdrun.executable

        mdcmd = self.mdrun.prepare_cmd_arguments(self.mdrunsubdir)
        cfdcmd = self.cfdrun.prepare_cmd_arguments(self.cfdrunsubdir)

        md  = self.mdexec  + " " + mdcmd
        cfd = self.cfdexec + " " + cfdcmd

        if self.platform == 'archer':
            # On ARCHER we cannot include command arguments in
            # MPMD mode so we need to create a mini-script
            mdrunfile = self.rundir + "/run_md.py"
            with open(mdrunfile, "w+") as f:
                f.write(runfilestr.replace("RUNCMDHERE", md))
            self.build = sp.Popen("chmod +x "+ mdrunfile, shell=True)
            md = mdrunfile

            cfdrunfile = self.rundir + "/run_cfd.py"
            with open(cfdrunfile, "w+") as f:
                f.write(runfilestr.replace("RUNCMDHERE", cfd))
            self.build = sp.Popen("chmod +x "+ cfdrunfile, shell=True)
            cfd = cfdrunfile

        if self.mpiexec == "cplexec":
            
            cmd = (self.mpiexec + " -m " + str(self.mdprocs) + " '"+md+"' "
                                + " -c " + str(self.cfdprocs) + " '"+cfd+"' "
                                + extra_cmds)
        else:
            if self.cmd_includes_procs():
                cmd = (self.mpiexec + " -n " + str(self.mdprocs)  + " "  + md 
                           +  " : " + " -n " + str(self.cfdprocs) + " "  + cfd
                                + extra_cmds)
            else:
                cmd = self.mpiexec + " " + md + " : " + cfd + extra_cmds

        return cmd

    def finish(self):
        self.mdrun.finish()
        self.cfdrun.finish()
