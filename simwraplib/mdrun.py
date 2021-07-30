#! /usr/bin/env python
import os
import errno
import shlex
import subprocess as sp
import shutil as sh
import string

import simwraplib.userconfirm as uc
from simwraplib.platform import get_platform
from simwraplib.inpututils import MDInputMod
from simwraplib.hpc import PBSJob
from simwraplib.gnuplotutils import GnuplotUtils
from simwraplib.run import Run, inheritdocstring


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

class MDRun(Run, metaclass=inheritdocstring):

    def __init__(self, 
                 srcdir='../MD_dCSE/src_code/',
                 basedir='../MD_dCSE/src_code/',
                 rundir='../MD_dCSE/runs/',
                 executable='./parallel_md.exe',
                 inputfile='MD.in',
                 outputfile='MD.out',
                 inputchanges={},
                 initstate=None,
                 restartfile=None,
                 jobname='default_jobname',
                 walltime='24:00:00',
                 extraargs={},
                 queue='',
                 platform=None,
                 extrafiles=None, 
                 finishargs={},
                 dryrun=False,
                 deleteoutput=False,
                 minimalcopy=False):

        #Inherit constructor from base class
        super(MDRun, self).__init__(srcdir=srcdir, 
                                    basedir=basedir, 
                                    rundir=rundir, 
                                    executable=executable,
                                    inputfile=inputfile, 
                                    outputfile=outputfile, 
                                    inputchanges=inputchanges,
                                    initstate=initstate, 
                                    restartfile=restartfile, 
                                    jobname=jobname, walltime=walltime, 
                                    extraargs=extraargs, queue=queue, 
                                    platform=platform,
                                    extrafiles=extrafiles, 
                                    finishargs=finishargs, 
                                    dryrun=dryrun,
                                    deleteoutput=deleteoutput,
                                    minimalcopy=minimalcopy)


        # Check input file exists and if not, for special case of MD.in
        # convert default.in so simulation will run
        if not os.path.isfile(basedir+inputfile):
            print((basedir+inputfile + " not found, attempting to convert default.in to MD.in"))
            if inputfile == "MD.in":
                sh.copy(basedir+"default.in", basedir+inputfile)
            else:
            #    pass
                raise IOError("No such file or directory: " +  basedir+inputfile)

        # Set input modifier to be normal kind
        self.inputmod = MDInputMod

    def build_executable(self, debug=False, platform="intel"):

        """
           Trigger a (re)build of specified executable from
           the source code directory
                
        """

        print("Attempting to build code from executable")
        print("Note that this is not really the responsisbility")
        print("of simwraplib which expects the user to have done this")

        #First try make
        try:
            if debug:
                cmdstg = 'make debug_p ' + "PLATFORM=" + platform + " " + self.executable
            else:
                cmdstg = 'make p ' + "PLATFORM=" + platform + " " + self.executable
  
            #Call build and wait until build has finished 
            #before returning control to caller
            split_cmdstg = shlex.split(cmdstg)
            self.build = sp.Popen(split_cmdstg, cwd=self.srcdir)      
            self.build.wait()

        except:
            print("Build Failed, try building manually before running simwraplib")
            raise


        #Check source code executable against run directory executable
#        if self.basedir != self.srcdir:
#            cmdstr = 'diff '
#            cmdstr += self.basedir + self.executable
#            cmdstr += self.srcdir  + self.executable
#            split_cmdstg = shlex.split(cmdstg)
#            diffexec = sp.check_output(split_cmdstg)
#            print(diffexec)

        return

    def setup(self, existscheck=False):

        # Do the normal creation of the run directory
        self.create_rundir(existscheck=existscheck)

        # Make a snapshot of the source code and store in a tarball
        if not self.minimalcopy:
            cmd = 'tar -cPf ' + self.rundir + 'src.tar ' + self.srcdir+'/*.f90'
            print(cmd)
            sp.Popen(cmd,shell=True)

        try:
            # Copy post_proc folder from base directory (if not there already)
            sh.copytree(self.basedir+'post_proc/',self.rundir+'post_proc/')
        except OSError:
            pass

        # Copy files and save new locations to instance variables
        for f in self.copyfiles:

            # Do nothing if the files are the same
            if (self.basedir+f == self.rundir+f):
                pass
            else:
                sh.copy(self.basedir+f, self.rundir+f)

        # Make changes to the input file once it has been copied
        self.prepare_inputs()

        mkdir_p(self.rundir+"./results")

    def get_nprocs(self):

        with open(self.rundir+self.inputfile,'r') as f:

            for line in f:
                if ('PROCESSORS' in line):
                    if ("#" not in line):
                        npx = int(next(f)) 
                        npy = int(next(f)) 
                        npz = int(next(f)) 
                    else:
                        npx = npy = npz = 1
                    break
        return npx*npy*npz

    def prepare_cmd_arguments(self, fdir=''):

        self.cmd_args = ' -i ' + fdir + self.inputfile
        if self.startfile != None:
            self.cmd_args += ' -r ' + fdir + self.startfile

        return self.cmd_args

    def finish(self):
        
        """
            Perform a selection of actions once the simulation has finished.
   
            self.finishargs must be a list of lists, of the form:
            
                [['keyword', object], ... ]
 
            Keyword options:
        
                final_state - when not None, move the results/final_state
                              file to a specified string (object) location.

                python_script - with object specifying pythonscriptdir, 
                                pyscriptname and [arg1,arg2,etc...] 
                
                etc., see below

        """

        class SimIncompleteError(Exception):
            pass

        # Check if run has finished correctly, otherwise try to print 
        # error messages and standard out to allow debugging
        #Setup standard out and standard error files
        stdoutfile = self.rundir+self.outputfile
        stderrfile = self.rundir+self.outputfile+'_err'
        #Look for time taken output written at end of run in last 10 lines
        try:
            with open(stdoutfile,'r') as fileObj:
                lastlines = fileObj.readlines()[-10:]
                finished_correctly = False
                for line in lastlines:
                    if "Time taken by code" in line:
                        timetaken = line.split(';')[1]
                        finished_correctly = True
            if finished_correctly==False:
                raise SimIncompleteError 
            else:
                print(('Simulation in directory ' + self.rundir + ' appears ' + 
                      'to have finished correctly in ' + timetaken + ' seconds,\n'
                       + 'the input file was ' + self.inputfile + '.'))
        #If time taken output is not found, display the last 10 lines of error and output info 
        except SimIncompleteError:
            print(('Simulation in directory ' + self.rundir + ', with input file\n'
                  + self.inputfile + ', appears to have failed:'))
            with open(stderrfile,'r') as fileObj:
                print((' ==== Standard Error File for rundir ' + self.rundir + ' ==== '))
                lastlines = fileObj.readlines()[-10:]
                for line in lastlines:
                    print(line)
            with open(stdoutfile,'r') as fileObj:
                print((' ==== Standard output File ' + self.rundir + ' ==== '))
                lastlines = fileObj.readlines()[-10:]
                for line in lastlines:
                    print(line)
        except IOError:
            print(('Unable to open stdoutfile' + stdoutfile + ' and stderrfile' 
                 + stderrfile + ' to check for simulation completion. '))

        # Run requested post processing scripts
        for entry in self.finishargs:

            key = entry[0]
            value = entry[1]

            if key == 'final_state':
                
                src = self.rundir + 'results/final_state'
                dst = self.rundir + value
                print(('Moving ' + src + ' to ' + dst))
                sh.move(src,dst)

            if key == 'python_script':
                 pass
                 #Go to directory, import function and call
#                  sys.path.append(value[0])
#                  try:
#                      import value[1] as pp_fn
#                  except: ImportError
#                      raise
#                  print('Calling post processing function ' + value[1] + 
#                        'in directory '+ value[0]+ 'with arguments ' + value[2])
#                  pp_fn(value[2])

            if key == 'gnuplot_script':

                outfile = 'tempout'
                gnufile = GnuplotUtils(value)
                gnufile.specify_outputfile(rundir=self.rundir,
                                           outfilename=outfile)
   
                #Run gnuplot and generate outputs
                cmdstr = ' gnuplot ' + value
                gnurun = sp.Popen(shlex.split(cmdstr),cwd=self.rundir)
                print(('Running gnuplot script ' + value +
                      ' with output ' + outfile))
                gnurun.wait()

                #Copy results back to calling directory and name by rundir
                sh.copy(self.rundir+outfile, outfile)
                valid_chars = "-_.() %s%s" % (string.ascii_letters, 
                                              string.digits)
                newname = ''.join((c for c in outfile+self.rundir 
                                   if c in valid_chars[6:]))
                os.rename(outfile, newname)
            
            if key == 'copy_resultsdir':
               
                src = self.rundir + 'results/'
                dst = self.rundir + value 
                print(('Copying ' + src + ' to ' + dst)) 
                if os.path.exists(dst):
                    sh.rmtree(dst)
                sh.copytree(src,dst)

            if key == 'reorder_restart':
           
                statefile = value[0] 
                inputfile = value[1]
                sh.copy(self.basedir+'reorder_restart',
                        self.rundir +'reorder_restart')
                cmd = './reorder_restart -r ' + statefile + ' -i ' + inputfile
                run = sp.Popen(shlex.split(cmd),cwd=self.rundir)
                run.wait() 
                sh.move(self.rundir+'final_state2',
                        self.rundir+statefile)

        if self.deleteoutput:
             remove_directory(confirm=False)


        return

