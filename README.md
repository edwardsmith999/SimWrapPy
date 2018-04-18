# SimWrapPy

A wrapper which allows parameter simulation of LAMMPS, OpenFOAM, Flowmol and coupled simulations.

## Key Features

 - A wrapper which creates a folder with copies of everything needed for a self contained and repeatable run (including source code. 
 - A set of input utilities which allow the quick construction of permutations and combinations (using overloaded add/multiply).
 - A higher level interface for running codes with a key set of functions: setup, run and finish. The base run class specifies a lot of the difficult task of depolying on vaious supercomputing platforms using PBS submission scripts.
 - The thread and study class allows multiprocessor parallelism by queing jobs to utilise the available resources using an internal semiphore system. 
 - A framework to setup coupled simulations (setup with http://www.cpl-library.org/) as a combination of multiple run objects.

## Structure and Objects

At the top level, you create a study. Each study contains a number of threads which each run using the multiprocessor framework in Python. You can specify how many to run at the same time based on the compute resource you have available.
  - study
  - thread
  - run

## Quickstart

When instatiated, Run should create a new folder as a "run" 
directory (if it doesn't already exist) and copy the necessary files 
from a "base" directory into it. All the information necessary for
execution of the run is stored from the following inputs to the
constructor: 

    Directories:

        srcdir  - path to source code folder
        basedir - path from which input/restart/etc files are copied
        rundir  - path in which the run will take place, files are 
                  copied from basedir to here.

    Copied files:

        executable   - name of executable (e.g. a.out)
        inputfile    - input file name
        extrafiles   - a List of additional files copied to rundir
        initstate    - initial state file that is TO BE COPIED 
                       FROM THE BASE DIRECTORY
        restartfile  - initial state "restart" file, assumed to be
                       already located at the given path that is
                       RELATIVE TO THE RUN DIRECTORY

    New files: 

        outputfile - output file name

    Other:

        inputchanges - dictionary of changes to make to the inputfile
                       once copied from the base directory
        finishargs   - list of lists: keywords and associated commands 
                       that specify a range of actions to perform
                       when the execution of the run has finished. See
                       the comments at the top of finish() for more
                       info. 
        


Example usage from a higher level:

    run = Run('../MD/src_code/', etc.)
    run.setup()
    run.execute()
    run.finish()


