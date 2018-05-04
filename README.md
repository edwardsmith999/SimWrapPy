# SimWrapPy

A wrapper which allows parameter simulation of LAMMPS, OpenFOAM, Flowmol and coupled simulations.

## Key Features

 - A wrapper which creates a folder with copies of everything needed for a self contained and repeatable run (including source code.
 - A set of input utilities which allow the quick construction of permutations and combinations (using overloaded add/multiply).
 - A higher level interface for running codes with a key set of functions: setup, run and finish. The base run class specifies a lot of the difficult task of deploying on various supercomputing platforms using PBS submission scripts.
 - The thread and study class allows multiprocessor parallelism by queuing jobs to utilise the available resources using an internal semaphore system.
 - A framework to setup coupled simulations (setup with http://www.cpl-library.org/) as a combination of multiple run objects.
 

## Structure and Objects

At the top level, you create a study. Each study contains a number of threads which each run using the multiprocessor framework in Python. You can specify how many to run at the same time based on the compute resource you have available.
  - study - manages the running of all threads in blocks based on specified max number of cpus
  - thread - a subprocess running on a thread (should be one per cpu)
  - run - an object which creates the folder structure, changes inputs and runs the specified executable
  - inpututils - helper functions to change input files for various codes
All runs are defined in terms of an existing code directory with src code, an executable, the location of the  input files and the directory in which to run. 
The user then specifies changes to this base directory to be made in each of the different runs.
 
## Quickstart

Consider the minimal example in the examples folder: minimal_example.py

```python
#! /usr/bin/env python2.7
import sys
sys.path.append("../")
import simwraplib as swl

# Inputs that are the same for every thread
basedir = './minimal_example/'
srcdir =  basedir + "src/"
executables = 'bin/hello.py'
inputfile = 'input/inputfile'

#Setup a set of changes for all permutations of two variables
inputs1 = swl.InputDict({"variablename": [i for i in range(3)]})
inputs2 = swl.InputDict({"othervariablename": [i for i in range(3)]})
changes = inputs1 * inputs2
filenames = changes.filenames(seperator="_")

#Loop over all changes and create a run object for each
threadlist =[]
for thread, change in enumerate(changes):
     rundir = basedir + '/runs/' + filenames[thread]
     run = swl.MinimalRun(srcdir, basedir,rundir,
                          executables,inputfile,
                          inputchanges=change)

     #One run for this thread (i.e. no setup run before main run)
     runlist = [run]
     threadlist.append(runlist)

# Number of cpus to use (run in blocks of 4)
ncpus = 4

# Run the study
study = swl.Study(threadlist, ncpus)
```

The python script in `./minimal_example/bin`, called `hello.py` which reads and prints a file is then run 9 times,

```python
with open("./input/inputfile") as f:
    filestr = f.read().split("\n")
    print("Hello World " + filestr[1] + " " + filestr[3] + "\n")
```

each in a seperate directory under run. The input file `inputfile` from `./minimal_example/input` is asjusted for each case

    variablename
    3
    othervariablename
    2
    
and stored for each directory.
The `./minimal_example/src` directory is also packaged up as a tarball in each case.

## Run Objects

When instantiated, Run should create a new folder as a "run"
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

```python
run = Run('../MD/src_code/', etc.)
run.setup()
run.execute()
run.finish()
```

The most important input for a parameter study is the `inputchanges` which specifies how
the input file is to be changed before running the code. The next section details how we set this up. 


## InputUtils

A set of utilities for creating parameter studies in a quick and intuitive way.

Specifying the input changes are done as a dictionary with the keywords you'd like to change with the corresponding value as a list of what you'd like to set the simulation input parameters to:

```python
inputs1 = swl.InputDict({'cells': [[8, 8, 8], [16, 16, 16]]})
inputs2 = swl.InputDict({'processors': [1, 1, 1], [2, 2, 2]})
```

We can then specify the parameter study for corresponding pair by adding

```python
changes = inputs1 + inputs2
```

where `changes` is then a list of paired dictonaries:

```python
[{'cells': [8, 8, 8], 'processors': [1, 1, 1]},
 {'cells': [16, 16, 16], 'processors': [2, 2, 2]}]
```

Alternatively we could multiply to get all permutations,

```python
changes = inputs1 * inputs2
```    

which would give 4 different sets of changes to an input,

```python
[{'cells': [8, 8, 8], 'processors': [1, 1, 1]},
 {'cells': [8, 8, 8], 'processors': [2, 2, 2]},
 {'cells': [16, 16, 16], 'processors': [1, 1, 1]},
 {'cells': [16, 16, 16], 'processors': [2, 2, 2]}]
```

### OpenFOAM input changes

The input changes to openFOAM works as follows:

Currently support for  `cell`, `domainsize`,
`origin` and `process` keywords with list of three
values for each. 
The user can also specify the full
OpenFOAM format in the slightly cumbersome but completely
consistent form of nested dicts/lists, for example to set cells

```python
keyword = "blockMeshDict"
keyvals = {"blocks":{"hex":["keep",[8,8,8],"keep","keep"]}}
```

where the "keep" keyword says to skip replacing values.
Also, to set processors, we need to change `numberOfSubdomains` 
and `simpleCoeffs` in the input file.

```python
keyword = ["decomposeParDict", "decomposeParDict"]
keyvals = [{"numberOfSubdomains":8},
           {"numberOfSubdomains":{simpleCoeffs:{"n":[2,2,2]}}}]
```

 ### LAMMPS input changes
 
The LAMMPS input file can be adapted as follows:
 
Replace values in a file where
we find a keyword on the line. For example
from LAMMPS (with random spacing):

    variable            maxy equal 2.0
    variable minz equal 0.0
    variable    maxz equal 2.0

    lattice fcc ${lat_scale}
    region reg block ${minx} ${maxx} ${miny} ${maxy} ${minz} ${maxz} units box
    create_box          1 reg
    create_atoms        1 region porous units box
    set     type 1 diameter ${diameter} density ${density}

    neighbor    5e-03 bin
    neigh_modify     once yes exclude type 1 1
    ...
    fix  5 all cpl/init region all forcetype Drag Cd ${Cd} sendtype granfull

The replace input strings then can be a unique combination of words
which identify the first part of the string, e.g.

    replace_input("variable maxz", "equal 1.0")

also you can specify a keyword hidden half way along the string
where only the part after that word needs to be specified.

    replace_input("cpl/init", "region all forcetype Drag Cd 5.0 sendtype granfull")

Note, multiple spacing is reduced to one in both input and keywords.
 
 ### Other input changes

Other formats include lines with a number followed by a comment

    3.14159     !PI
    42          !Meaning of life

and keyword as used in CPL, e.g.

    SOMEKEYWORD
    1
    2

where the two values can be changed

## Setting up a study

Now we have a set of changes and we know how to create run objects, we want to setup a study by creating a list of run directories to pass to study.

```python
#Set the maximum number of cpus to use for these runs
ncpus = 6

#Get the folder/file name to store run for each change
baserundir = "/path/to/dir/to/store/runs"
filenames = changes.filenames(seperator="_")

threadlist =[]
for thread, change in enumerate(changes):
     rundir = baserundir + filenames[thread]

     run = swl.LammpsRun(
                         srcdir,
                         basedir,
                         rundir,
                         executables,
                         inputfile,
                         outputfile,
                         queue='general',
                         platform="local",
                         walltime='00:02:00',
                         inputchanges=change,
                         finishargs = {},
                         dryrun=False
                        )
     #One run for this thread (i.e. no setup run before main run)
     runlist = [run]
     threadlist.append(runlist)
     print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

# Run the study
study = swl.Study(threadlist, ncpus)
```



