#! /usr/bin/env python2.7
import numpy as np
import matplotlib.pyplot as plt
import string
import itertools
import sys
import multiprocessing

sys.path.append('../')
import simwraplib as swl

def openfoam_scaling_changes(process = np.array([2, 3, 4]),
                             basecells = np.array([48, 48, 48]),
                             basesize=np.array([1., 1., 1.]),
                             nsteps=2):

    # Specify input file changes for each thread 
    # Processors in block of 24 up to 2304   
    units = basecells
    size = basesize
    j = 0
    plist = []; ulist = []; dlist = []
    for case in range(nsteps):
        plist.append(process.tolist())
        ulist.append(units.tolist())
        dlist.append(size.tolist())
        process[j] = process[j]*2
        units[j] = basecells[j]*2
        size[j] = basesize[j]*2
        j = (j+1)%3
        print(case, j, process, np.product(process))

    inputs1 = swl.InputDict({'process' : plist})
    inputs2 = swl.InputDict({"cell" : ulist})
    inputs3 = swl.InputDict({'domainsize' : dlist})
    changes = inputs1+inputs2+inputs3

    return changes

def scaling_openfoam(fdir, srcdir, executables, inputfile, changes):

    # Inputs that are the same for every thread
    basedir = fdir
    outputfile = 'openfoam.out'
    finish = [{'final_state':'final_state'}]

    #Get filename from changes
    filenames = changes.filenames(seperator="_")
    print(filenames)

    #Create a range of run objects
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
            'OpenFOAM-3.0.1_coupled/' +
            'CPL_APP_OPENFOAM-3.0.1/')
    srcdir =  fdir + "src/"   
    executables = 'bin/CPLSediFOAM'
    inputfile = 'run/openfoam'
    changes = openfoam_scaling_changes()
    threadlist = scaling_openfoam(fdir, srcdir, executables, 
                                  inputfile, changes)
    print(threadlist)
    study = swl.Study(threadlist, ncpus)

