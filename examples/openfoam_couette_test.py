#! /usr/bin/env python2.7
import numpy as np
import matplotlib.pyplot as plt
import string
import itertools
import sys
import multiprocessing
import MDAnalysis

sys.path.append('../')
import simwraplib as swl

# Number of threads and runs per thread
ncpus = 1
maxlicenses = ncpus

# Inputs that are the same for every thread
fdir = '/home/es205/codes/cpl_granlammmps/OpenFOAM-3.0.1_LAMMPS-dev/OpenFOAM-3.0.1_coupled/CPL_APP_OPENFOAM-3.0.1/'
srcdir =  fdir + "src/"
basedir = fdir
executables = 'bin/CPLSediFOAM'

# Specify information needed for each run
inputfile = 'run/openfoam'
outputfile = 'openfoam.out'
finish = [{'final_state':'final_state'}]

# Specify input file changes for each thread 
# Processors in block of 24 up to 2304
process = np.array([1, 1, 1])
units = np.array([8, 8, 8])

deltaT = 0.05
endTime = 10

ulist = []; dtlist = []
for case in range(12):
    ulist.append(units.tolist())
    #Need to scale dt to ensure CFL number
    newdeltaT = deltaT/np.sqrt(np.product(units/8.))
    newendTime = endTime/np.sqrt(np.product(units/8.))
    dtlist.append({"deltaT" : newdeltaT, 
                   "endTime" : newendTime,
                   "writeInterval" : 0.5*newendTime})
    j = case%3
    units[j] = 2*units[j]

    print(case, j, np.product(units), ulist[case], dtlist[case])

inputs1 = swl.InputDict({'cell': ulist})
inputs2 = swl.InputDict({'controlDict': dtlist})

changes = inputs1 + inputs2
filenames = changes.filenames(seperator="_")

print(changes, filenames)

threadlist =[]
for thread in range(0,len(changes)):
     rundir = srcdir + '../runs/' + filenames[thread]

     run = swl.OpenFOAMRun(
                         srcdir,
                         basedir,
                         rundir,
                         executables,
                         inputfile,
                         outputfile,
                         queue='ecse0803',
                         platform="local",
                         walltime='00:02:00',
                         inputchanges=changes[thread],
                         finishargs = {},
                         dryrun=False
                        )
     #One run for this thread (i.e. no setup run before main run)
     runlist = [run]
     threadlist.append(runlist)
     print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

# Run the study
study = swl.Study(threadlist,ncpus)

