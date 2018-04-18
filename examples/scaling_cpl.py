#! /usr/bin/env python2.7
import numpy as np
import matplotlib.pyplot as plt
import string
import itertools
import sys
import multiprocessing

sys.path.append('../')
import simwraplib as swl

from scaling_lmps import lammp_scaling_changes, scaling_lammps
from scaling_openfoam import openfoam_scaling_changes, scaling_openfoam

# Number of threads and runs per thread
ncpus = 1000000
maxlicenses = ncpus

# Inputs that are the same for every thread
fdir = "/home/es205/codes/cpl_granlammmps/OpenFOAM-3.0.1_LAMMPS-dev/"
srcdir = "/home/es205/codes/cpl/cpl-library/src/"
basedir = fdir + '/runs/baserun/'
inputfile = 'cpl/COUPLER.in'
outputfile = 'COUPLER.out'
finish = [{'final_state':'final_state'}]

Lx = 4.; Ly = 4.; Lz = 4.
changesl = lammp_scaling_changes(basesize=np.array([Lx, Ly, Lz]))
fdirl = fdir + 'LAMMPS-dev_coupled/CPL_APP_LAMMPS-DEV/'
lmpsthreads = scaling_lammps(fdirl, 'bin/lmp_cpl', 'examples/lammps.in', changesl)

changeso = openfoam_scaling_changes(basesize=np.array([Lx, Ly, Lz]))
fdiro = (fdir + 'OpenFOAM-3.0.1_coupled/CPL_APP_OPENFOAM-3.0.1/')
foamthreads = scaling_openfoam(fdiro, 'bin/CPLSediFOAM', 'run/openfoam', changeso)

assert len(foamthreads) == len(lmpsthreads)

threadlist =[]
for thread in range(len(foamthreads)):

    rundir = fdir + '/runs/' + str(thread)

    print(thread)

    executables = [lmpsthreads[thread][0], foamthreads[thread][0]]

    run = swl.CPLRun(
                     srcdir,
                     basedir,
                     rundir,
                     executables,
                     inputfile,
                     outputfile,
                     queue='ecse0803',
                     platform="local",
                     walltime='00:10:00',
                     inputchanges=[],
                     finishargs = {},
                     dryrun=True
                     )
     #One run for this thread (i.e. no setup run before main run)
    runlist = [run]
    threadlist.append(runlist)
    print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

## Run the study
study = swl.Study(threadlist,ncpus)

