#! /usr/bin/env python2.7
import sys

sys.path.append("../")
import simwraplib as swl


# Inputs that are the same for every thread
basedir = './minimal_example/'
srcdir =  basedir + "src/"
executables = 'bin/hello.py'
inputfile = 'input/inputfile'
outputfile = 'lammps.out'
finish = [{'final_state':'final_state'}]

inputs1 = swl.InputDict({"variablename": [i for i in range(3)]})
inputs2 = swl.InputDict({"othervariablename": [i for i in range(3)]})

changes = inputs1 * inputs2

filenames = changes.filenames(seperator="_")

print(filenames)

threadlist =[]
for thread, change in enumerate(changes):
     rundir = basedir + '/runs/' + filenames[thread]

     print('Run in directory '  + rundir + ' thread ' + str(thread))

     run = swl.MinimalRun(
                          srcdir,
                          basedir,
                          rundir,
                          executables,
                          inputfile,
                          inputchanges=change
                          )

     #One run for this thread (i.e. no setup run before main run)
     runlist = [run]
     threadlist.append(runlist)

# Number of threads and runs per thread
ncpus = 4

# Run the study
study = swl.Study(threadlist,ncpus)

