#! /usr/bin/env python2.7
import numpy as np
import sys

sys.path.append('../')
import simwraplib as swl

# Number of threads and runs per thread
ncpus = 1
maxlicenses = ncpus

# Inputs that are the same for every thread
fdir = '/home/es205/codes/cpl_granlammmps/OpenFOAM-3.0.1_LAMMPS-dev/LAMMPS-dev_coupled/CPL_APP_LAMMPS-DEV/'
srcdir =  fdir + "src/"
basedir = fdir
executables = 'bin/lmp_cpl'

# Specify information needed for each run
inputfile = 'examples/lammps.in'
outputfile = 'lammps.out'
finish = [{'final_state':'final_state'}]

# Specify input file changes for each thread 
# Processors in block of 24 up to 2304
process = np.array([1,1,1])
baseunit = np.array([0.2,0.2,0.2])
units =baseunit 
j = 0
zeros = []; xlist = []; ylist = []; zlist = []
for case in range(20): #range(10):
    units[j] = baseunit[j]*2
    j = (j+1)%3
    zeros.append([0.0])
    xlist.append([units[0]])
    ylist.append([units[1]])
    zlist.append([units[2]])
    print(case, j, units)

inputs = []    
v = "variable"; e = "equal"
inputs.append(swl.InputDict({v+" minx "+e: zeros}))
inputs.append(swl.InputDict({v+" maxx "+e: xlist}))
inputs.append(swl.InputDict({v+" miny "+e: zeros}))
inputs.append(swl.InputDict({v+" maxy "+e: ylist}))
inputs.append(swl.InputDict({v+" minz "+e: zeros}))
inputs.append(swl.InputDict({v+" maxz "+e: zlist}))

changes = inputs[0]
for i in inputs[1:]:
    changes = changes + i

filenames = changes.filenames(seperator="_")
filenames = [f.replace(v,"").replace(e,"") for f in filenames]

print(filenames)

threadlist =[]
for thread in range(0,len(changes)):
     rundir = srcdir + '../runs/' + filenames[thread]

     run = swl.LammpsRun(
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
                         dryrun=True
                        )
     #One run for this thread (i.e. no setup run before main run)
     runlist = [run]
     threadlist.append(runlist)
     print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

# Run the study
study = swl.Study(threadlist,ncpus)

