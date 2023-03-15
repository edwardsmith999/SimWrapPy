#! /usr/bin/env python
import os
import errno
import shlex
import subprocess as sp
import shutil as sh
import string

import simwraplib.userconfirm as uc
from simwraplib.platform import get_platform
from simwraplib.inpututils import OpenFOAMInputMod, reverse_readline
from simwraplib.hpc import PBSJob
from simwraplib.run import Run, inheritdocstring

class OpenFOAMRun(Run, metaclass=inheritdocstring):

    def __init__(self, 
                 srcdir='../src/',
                 basedir='../bin/',
                 rundir='../runs/',
                 executable='./CPLSediFOAM',
                 inputfile='openfoam',
                 outputfile='openfoam.out',
                 inputchanges={},
                 initstate=None,
                 restartfile=None,
                 jobname='openfoam_job',
                 walltime='00:09:00',
                 extraargs={},
                 queue='',
                 platform=None,
                 extrafiles=None, 
                 finishargs={},
                 dryrun=False,
                 deleteoutput=False):

        super(OpenFOAMRun, self).__init__(srcdir=srcdir, 
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
        self.inputmod = OpenFOAMInputMod

        extraargs["qscript_on_ARCHER2"] = (
"""
#!/bin/bash

#SBATCH --job-name=my_cpl_demo
#SBATCH --time=0:10:0
#SBATCH --exclusive
#SBATCH --export=none
#SBATCH --account=ecseaf01

#SBATCH --partition=standard
#SBATCH --qos=standard

#SBATCH --nodes=2

# single thread export overriders any declaration in srun
export OMP_NUM_THREADS=1

module load other-software
module load cpl-openfoam/2106
source $FOAM_CPL_APP/SOURCEME.sh

# using your own installtion: remove the last three lines and use these four lines instead
# remmeber to update the path to the two SOURCEME.sh files
#module load openfoam/com/v2106
#module load lammps/13_Jun_2022
#module load cray-python
#source
"""
+ " " + basedir + "/CPL_APP_OPENFOAM/SOURCEME.sh" +
"""

source SOURCEME.sh

#Got to work directory
cd $PBS_O_WORKDIR

#Clean up
rm -f qscript.*
rm -f output

#Clean OpenFOAM files in case 

"""
+ "cd ./" 
+ self.inputfile +
"""

python clean.py -f

# load restor0Dir tool
. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions        # Tutorial run functions
restore0Dir

blockMesh > log.blockMesh 2>&1
decomposePar > log.decomposePar 2>&1
cd ../

SHARED_ARGS="--distribution=block:block --hint=nomultithread"

srun ${SHARED_ARGS} --het-group=0 --nodes=1 --tasks-per-node=2 MD : --het-group=1 --nodes=1 --tasks-per-node=2
""" 
+ " " + executable + " -parallel" + 
"""

reconstructPar > log.reconstructPar 2>&1
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

    def prepare_inputs(self, extrachanges=None, **kwargs):

        """
            Make alterations to the base input file (specified on 
            construction) that will be copied into the run directory.
        
            The input "changes" should be a dictionary of the form:
            
            {'cell':[8,8,8], 'domainsize':[1.,10.,2.], 'origin' : [0.,0.,0.]
            'process':[1,1,1]}             
            The user can also specify the full keyword in a format which is cumbersome but completely 
            consistent with OpenFOAM, using nested dicts/lists based on the level
            of nesting in the input files, for example to set cells which is in the
            blockMeshDict input as:
                blocks
                (
	                hex (0 1 2 3 4 5 6 7) (160 40 40) simpleGrading (1 1 1)
                );
            We use:
                keyword = "blockMeshDict"
                keyvals = {"blocks":{"hex":["keep",[8,8,8],"keep"]}}

            here the nesting is 1) blockMeshDict file, 2) blocks 3) hex with
            values of hex set on the line. Only items in brackets are targets to change 
            (no simpleGrading keyword) and the "keep" keyword says to skip 
            replacing any values in the brackets.
            To set processors with format:

                numberOfSubdomains    48;

                ...

                simpleCoeffs
                {
                    n               (4 3 4);
                    delta           0.001;
                }

            We use two seperate call but to the same file,
            keyword = ["decomposeParDict", "decomposeParDict"]
            keyvals = [{"numberOfSubdomains":8}, 
                       {"numberOfSubdomains":{"simpleCoeffs":{"n":[2,2,2]}}}]
            changes = dict(zip(keyword, keyvals))

            which ends up being a single dictonary entry for decomposeParDict.

            Disclaimer:
            This may not work as expected in all case given how complex
            and apparently inconsistent the OpenFOAM input system is.
                
        """

        #Openfoam input is a sirectory, not a file. Check this
        if os.path.isdir(self.rundir+self.inputfile):
            self.inputmod = self.inputmod(self.rundir+self.inputfile)
        else:
            raise IOError("OpenFOAM input " + self.rundir+self.inputfile + " not found")


        #If additional changes, add these to the input changes
        if (extrachanges):
            self.inputchanges.update(extrachanges)

        for key in self.inputchanges:
            values = self.inputchanges[key]
            self.inputmod.replace_input(key, values)    
        
        return

    def get_nprocs(self):

        nprocs = int(self.inputmod.HD['decomposeParDict']["numberOfSubdomains"])
        
        return nprocs

    def prepare_cmd_arguments(self, fdir=''):

        self.cmd_args = ' -case ' + fdir + self.inputfile
        self.cmd_args += " -parallel "

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
            lastlines = fileObj.readlines()[-10:]
            for line in lastlines:
                if "ExecutionTime" in line:
                    print(("ExecutionTime in directory ", 
                          self.rundir.split("/")[-2], 
                          " is ", line.split()[2]))
