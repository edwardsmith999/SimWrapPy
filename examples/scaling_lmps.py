#! /usr/bin/env python2.7
import numpy as np
import matplotlib.pyplot as plt
import string
import itertools
import sys
import multiprocessing

sys.path.append('../')
import simwraplib as swl

def lammp_scaling_changes(process = np.array([2,3,4]),
                          basesize = np.array([4.,4.,4.]),
                          nsteps=12):

    # Specify input file changes for each thread 
    # Processors in block of 24 up to 2304
    units = basesize 
    j = 0
    plist = []; zeros = []; xlist = []; ylist = []; zlist = []
    for case in range(nsteps):
        plist.append(process.tolist())
        xlist.append([units[0]])
        ylist.append([units[1]])
        zlist.append([units[2]])
        process[j] = process[j]*2
        units[j] = basesize[j]*2
        j = (j+1)%3
        zeros.append([0.0])
        print(case, j, process, np.product(process))

    inputs = []    
    v = "variable"; e = "equal"
    inputs.append(swl.InputDict({v+" minx "+e: zeros}))
    inputs.append(swl.InputDict({v+" maxx "+e: xlist}))
    inputs.append(swl.InputDict({v+" miny "+e: zeros}))
    inputs.append(swl.InputDict({v+" maxy "+e: ylist}))
    inputs.append(swl.InputDict({v+" minz "+e: zeros}))
    inputs.append(swl.InputDict({v+" maxz "+e: zlist}))

    changes = swl.InputDict({'processors': plist})
    for i in inputs:
        changes = changes + i

    return changes

def scaling_lammps(fdir, srcdir, executables, inputfile, changes):

    # Inputs that are the same for every thread
    basedir = fdir

    # Specify information needed for each run
    outputfile = 'lammps.out'
    finish = [{'final_state':'final_state'}]

    #Get filename from changes
    filenames = changes.filenames(seperator="_")
    v = "variable"; e = "equal"
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
                             platform="archer",
                             walltime='00:10:00',
                             inputchanges=changes[thread],
                             finishargs = {},
                             dryrun=False
                            )
         #One run for this thread (i.e. no setup run before main run)
         runlist = [run]
         threadlist.append(runlist)
         print('Run in directory '  + rundir + 
               ' and dryrun is '  + str(run.dryrun))

    return threadlist

# Run the study
if __name__ == "__main__":
    # Number of threads and runs per thread
    ncpus = 6
    maxlicenses = ncpus
    fdir = ('/home/es205/codes/cpl_granlammmps/' + 
            'OpenFOAM-3.0.1_LAMMPS-dev/' + 
            'LAMMPS-dev_coupled/CPL_APP_LAMMPS-DEV/')
    srcdir =  fdir + "src/"
    executables = 'bin/lmp_cpl'
    inputfile = 'examples/lammps.in'
    changes = lammp_scaling_changes()
    threadlist = scaling_lammps(fdir, srcdir, executables, 
                                inputfile, changes)
    study = swl.Study(threadlist, ncpus)

