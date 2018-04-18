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
ncpus = 6
maxlicenses = ncpus
nsteps = 1

# Inputs that are the same for every thread
fbase = "/home/es205/codes/cpl_granlammmps/OpenFOAM-3.0.1_LAMMPS-dev/"
fdir = fbase + "runs/baserun/"
srcdir = "/home/es205/codes/cpl/cpl-library/src/"
basedir = fdir
inputfile = 'cpl/COUPLER.in'
outputfile = 'COUPLER.out'
finish = [{'final_state':'final_state'}]


process = np.array([1, 1, 1])
basesize = np.array([1., 1., 1.])
changesl = lammp_scaling_changes(process=process, basesize=basesize, nsteps=nsteps)
fsrcl = fbase + 'LAMMPS-dev_coupled/CPL_APP_LAMMPS-DEV/'
lmpsthreads = scaling_lammps(fdir, fsrcl, 'bin/lmp_cpl', 'lammps/lammps.in', changesl)

print("LAMMPS OBJECT")

process = np.array([1, 1, 1])
basecells = np.array([6, 12, 6])
basesize = np.array([1., 1., 1.])
changeso = openfoam_scaling_changes(process, basecells, basesize, nsteps=nsteps)
fsrco = fbase + 'OpenFOAM-3.0.1_coupled/CPL_APP_OPENFOAM-3.0.1/'
foamthreads = scaling_openfoam(fdir, fsrco, 'bin/CPLSediFOAM', './openfoam', changeso)

print("OPENFOAM OBJECT")

assert len(foamthreads) == len(lmpsthreads)

threadlist =[]
for thread in range(len(foamthreads)):

    rundir = fdir + '../' + str(thread)

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
                     dryrun=False
                     )
     #One run for this thread (i.e. no setup run before main run)
    runlist = [run]
    threadlist.append(runlist)
    print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

## Run the study
study = swl.Study(threadlist,ncpus)

