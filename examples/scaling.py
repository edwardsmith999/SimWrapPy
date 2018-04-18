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
ncpus = 1000000
maxlicenses = ncpus

# Inputs that are the same for every thread
srcdir =  '../../flowmol/src/'
basedir = srcdir
executables = './parallel_md.exe'

# Specify information needed for each run
inputfile = 'MD.in'
outputfile = 'MD.out'
finish = [{'final_state':'final_state'}]

# Specify input file changes for each thread 
# Processors in block of 24 up to 2304
process = np.array([2,3,4])
baseunit = np.array([40,40,40])
units =baseunit 
j = 0
plist = []; ulist = []
for case in range(10):
    process[j] = process[j]*2
    units[j] = baseunit[j]*process[j]
    j = (j+1)%3
    plist.append(process.tolist())
    ulist.append(units.tolist())
    print(case, j, process, np.product(process))
    
inputs1 = swl.InputDict({'PROCESSORS': plist})
inputs2 = swl.InputDict({"INITIALNUNITS": ulist})
changes = inputs1+inputs2
filenames = changes.filenames(seperator="_")

print(filenames)

threadlist =[]
for thread in range(0,len(changes)):
     rundir = srcdir + '../runs/' + filenames[thread]

     run = swl.MDRun(
                  srcdir,
                  basedir,
                  rundir,
                  executables,
                  inputfile,
                  outputfile,
                  queue='ecse0803',
                  platform="archer",
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

