#! /usr/bin/env python
import os
import errno
import shlex
import subprocess as sp
import shutil as sh
import string

import simwraplib.userconfirm as uc
from simwraplib.platform import get_platform
from simwraplib.inpututils import LammpsInputMod
from simwraplib.hpc import PBSJob
from simwraplib.run import Run, inheritdocstring

class LammpsRun(Run):
        
    __metaclass__ = inheritdocstring

    def __init__(self, 
                 srcdir='../src/',
                 basedir='../bin/',
                 rundir='../runs/',
                 executable='./lmp_cpl',
                 inputfile='lammps.in',
                 outputfile='lammps.out',
                 inputchanges={},
                 initstate=None,
                 restartfile=None,
                 jobname='lammps_job',
                 walltime='00:09:00',
                 extraargs={},
                 queue='',
                 platform=None,
                 extrafiles=None, 
                 finishargs={},
                 dryrun=False,
                 deleteoutput=False):

        #Inherit constructor from base class
        super(LammpsRun, self).__init__(srcdir=srcdir, 
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


        # Set input modifier to be normal kind
        self.inputmod = LammpsInputMod

        extraargs["qscript_on_ARCHER"] = (
"""
module load python-compute/2.7.6
module load pc-numpy
module unload PrgEnv-cray
module load PrgEnv-gnu
module unload gcc/6.3.0
module load gcc/5.1.0

export CRAYPE_LINK_TYPE=dynamic

#Got to work directory
cd $PBS_O_WORKDIR

#Clean up
rm -f qscript.*
rm -f output

#Avoid OpenMP
export OMP_NUM_THREADS=1

#Not sure we need absolute path here 
cd $PBS_O_WORKDIR
""")

    def build_executable(self, debug=False, platform="intel"):

        """
           Trigger a (re)build of specified executable from
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


    def get_nprocs(self):

        with open(self.rundir+self.inputfile,'r') as f:

            for line in f:
                if ('processors' in line):
                    lst = line.split()
                    npx = int(lst[1]) 
                    npy = int(lst[2]) 
                    npz = int(lst[3]) 
                    break
        
        return npx*npy*npz

    def prepare_cmd_arguments(self, fdir=''):

        self.cmd_args = ' -in ' + fdir + self.inputfile

        #Add restart to first line of input file
        if self.startfile != None:
            with open(self.rundir+self.inputfile, 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.write("read_restart " + self.startfile + "\n")

        return self.cmd_args


    def finish(self):

        if self.dryrun:
            return

        # Check if run has finished correctly, otherwise try to print 
        # error messages and standard out to allow debugging
        #Setup standard out and standard error files
        stdoutfile = self.rundir+self.outputfile
        stderrfile = self.rundir+self.outputfile+'_err'

        #Look for time taken output written at end of run in last 10 lines

        with open(stdoutfile,'r') as fileObj:
            lastlines = fileObj.readlines()[-40:]
            for line in lastlines:
                if "Loop time" in line:
                    print("ExecutionTime in directory ", self.rundir.split("/")[-2],
                          " is ", line.split()[3])
#                if "Total wall time" in line:
#                    print("ExecutionTime in directory ", self.rundir.split("/")[-2],
#                          " is ", float(line.split(":")[-1].replace("\n",""))
#                             + 60*float(line.split(":")[-2])
#                           + 3600*float(line.split(":")[-3].split()[-1]))

