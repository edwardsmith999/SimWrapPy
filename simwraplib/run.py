 # Only Python 2.x
import os
import errno
import shutil as sh
import subprocess as sp
import inspect
import shlex
import sys

import simwraplib.userconfirm as uc
from simwraplib.platform import get_platform
from simwraplib.hpc import PBSJob

def get_subprocess_error(e):
    print("subprocess ERROR")
    import json
    error = json.loads(e[7:])
    print(error['code'], error['message'])


def inheritdocstring(name, bases, attrs):
    if not '__doc__' in attrs:
        # create a temporary 'parent' to (greatly) simplify the MRO search
        temp = type('temporaryclass', bases, {})
        for cls in inspect.getmro(temp):
            if cls.__doc__ is not None:
                attrs['__doc__'] = cls.__doc__
                break

    return type(name, bases, attrs)

def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

class Run(object):

    """ 
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

            run = Run('../MD_dCSE//src_code/', etc.)
            run.setup()
            run.execute()
            run.finish()

    """
    
    def __init__(self, 
                 srcdir=None,
                 basedir=None,
                 rundir=None,
                 executable=None,
                 inputfile=None,
                 outputfile="output",
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
                 dryrun=True,
                 deleteoutput=False,
                 minimalcopy=False
                 ):

        if (basedir == None):
            self.basedir = ""
        elif (basedir is ""):
            self.basedir = ""
        else:
            #Add trailing slash
            self.basedir = basedir
            if (self.basedir[-1] != os.sep): 
                self.basedir += os.sep

            #Check base directory exists
            if not os.path.isdir(self.basedir):
                print("Basedir = ", self.basedir)
                raise IOError("Path "+self.basedir+" not found")

        #Check src directory exists
        self.srcdir = srcdir
        if (srcdir is not None):
            if (srcdir[-1] != os.sep): self.srcdir += os.sep
            if os.path.isdir(srcdir):
                self.srcdir = srcdir
            else:
                raise IOError("Path "+srcdir+" not found")
        else:
            self.srcdir = None

        if (rundir is None):
            raise IOError(rundir + " not specified")

        #Check rundir exists and make if not
        self.rundir = rundir
        if (self.rundir[-1] != os.sep): 
            self.rundir += os.sep
#        try:
#            os.makedirs(rundir)
#        except OSError as e:
#            if e.errno != errno.EEXIST:
#                raise

        #Check executable specified exist in basedir
        self.executable_on_path = False
        if (type(executable) is list):
            self.executable = executable
            for e in executable:
                if (type(e) is str):
                    if os.path.isfile(self.basedir+e):
                        raise IOError("Executable "+self.basedir+executable+" not found")
        else:
            #print(self.basedir+executable)
            if os.path.isfile(self.basedir+executable):
                self.executable = executable
            else:
                #See if executable is on path
                exepath = which(executable)
                if exepath != None:
                    self.executable = executable
                    self.executable_on_path = True
                else:
                    #Try to build exectuable
                    print("Executable "+self.basedir+executable+" not found, trying to build")
                    self.build_executable()
                    if not os.path.isfile(self.basedir+executable):
                        raise IOError("Executable "+self.basedir+executable+" not found")

        #Check inputfile specified exist in basedir
        if inputfile is not None:
            if os.path.isfile(self.basedir+inputfile):
                self.inputfile = inputfile
            else:
                #Check if folder
                if os.path.isdir(self.basedir+inputfile):
                    self.inputfile = inputfile
                else:
                    raise IOError("inputfile "+self.basedir+inputfile+" not found")
        else:
            #If input file is not defined, set to executable
            self.inputfile = None

        #Output file
        self.outputfile = outputfile

        #Dictonary of values to change in input file
        if type(inputchanges) is dict:
            self.inputchanges = inputchanges
        else:
            raise OSError("Input changes must be a dictonary of changes for a single RUN ONLY")

        # Check initstate and restartfile are not both specified
        if (initstate != None and restartfile != None):
            raise IOError('Error: both initial state and restart files are not None')
        #Check initstate or restartfile specified exist in basedir
        elif (initstate != None):
            if os.path.isfile(self.basedir+initstate):
                self.startfile = initstate
            else:
                raise IOError("initstate "+self.basedir+initstate+" not found")
        elif (restartfile != None):
            if os.path.isfile(self.basedir+restartfile):
                self.startfile = restartfile
            else:
                raise IOError("restartfile "+self.basedir+restartfile+" not found")
        else:
            self.startfile = None

        if (extrafiles):
            if type(extrafiles) is str:
                extrafiles = [extrafiles]
            for f in extrafiles:
                if not os.path.isfile(self.basedir+f):
                    raise IOError("extrafile "+self.basedir+f+" not found")

        #Other arguments
        self.extrafiles = extrafiles
        self.finishargs = finishargs
        self.dryrun = dryrun
        self.deleteoutput = deleteoutput
        self.minimalcopy = minimalcopy # If true, copy only input

        # Keep a list of files to iterate over later
        if type(executable) is str:
            self.copyfiles = [executable]
        else:
            self.copyfiles = []
        if (inputfile): self.copyfiles.append(inputfile)
        if (self.startfile): self.copyfiles.append(self.startfile)
        if (extrafiles): self.copyfiles += extrafiles

        # Work out what machine we're on
        if platform is None:
            self.platform = get_platform()
        else:
            self.platform = platform

        # Store more values if PBS/supercomputer run
        self.jobname = jobname
        self.walltime = walltime
        self.queue = queue 
        if type(extraargs) is dict:
            self.extraargs = extraargs 
        else:
            raise TypeError("extraargs input should be dictonary")


    def build_executable(self, buildstr=""):

        """
           Trigger a (re)build of specified executable from
           the source code directory
                
        """

        print("Attempting to build code from executable")
        print("Note that this is not really the responsisbility")
        print("of simwraplib which expects the user to have done this")

        #First try make
        try:
            cmdstg = 'make'
  
            #Call build and wait until build has finished 
            #before returning control to caller
            split_cmdstg = shlex.split(cmdstg)
            if self.srcdir != None:
                self.build = sp.Popen(split_cmdstg, cwd=self.srcdir)      
                self.build.wait()
            else:
                raise OSError("src directory not specified, cannot build")
        except:
            print("Build Failed, try building manually before running simwraplib")
            raise

    def copyfile(self, f):

        if f is None:
            return

        if (type(f) is list):
            for i in f:
                self.copyfile(i)
            return

        # Do nothing if the files are the same
        if sh._samefile(self.basedir+f, self.rundir+f):
        #if (self.basedir+f == self.rundir+f):
            return

        #Copy input folder if it is a directory
        if os.path.isdir(self.basedir+f):
            if os.path.isdir(self.rundir+f):
                self.remove_directory(folder=self.rundir+f, confirm=False)
            try:
                sh.copytree(self.basedir+f, self.rundir+f)
            except OSError:
                raise OSError("Error copying folder base = " + self.basedir+f
                                + " to run = " + self.rundir+f)

        #Otherwise copy a file (and maybe create base directory
        else:
            if not os.path.exists(os.path.dirname(self.rundir+f)):
                try:
                    os.makedirs(os.path.dirname(self.rundir+f))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            try:
                sh.copy(self.basedir+f, self.rundir+f)
            except OSError:
                raise OSError("Error copying file = " + self.basedir+d
                                    + " to run dir = " + self.rundir)
    
    def setup(self, existscheck=False):

        # Do the normal creation of the run directory
        self.create_rundir(existscheck=existscheck)

        # Make a snapshot of the source code and store in a tarball
        if not self.minimalcopy:
            if self.srcdir != None:
                cmd = 'tar -cPf ' + self.rundir + 'src.tar ' + self.srcdir
                sp.Popen(cmd, shell=True)

        # Copy files and save new locations to instance variables
        for f in self.copyfiles:
            if (self.executable_on_path and self.executable in f):
                #No need to copy executable if on path
                pass
            elif (self.minimalcopy and self.executable in f):
                 os.symlink(self.basedir+self.executable, 
                            self.rundir+os.sep+self.executable)
            else:
                self.copyfile(f)

            #print("Files = ", self.basedir+f, self.rundir+f)

        # Make changes to the input file once it has been copied
        self.prepare_inputs()

    def prepare_inputs(self, extrachanges=None, **kwargs):

        """
            Make alterations to the base input file (specified on 
            construction) that will be copied into the run directory.
        
            The inputmod "changes" should be a dictionary of the form:
            
                changes = { 'DENSITY': 0.8, 'INPUTTEMPERATURE': 1.0 , ...}    
                
        """

        mod = self.inputmod(self.rundir+self.inputfile)

        #If additional changes, add these to the input changes
        if (extrachanges):
            self.inputchanges.update(extrachanges)

        for key in self.inputchanges:
            values = self.inputchanges[key]
            print("run prepare_inputs, key=", key, "values=",values)

            mod.replace_input(key, values)    
        
        return

    def create_rundir(self, existscheck=False, **kwargs):

        # Create run directory (and results dir inside it). If it already
        # exists, ask the user if they want to carry on.
        try:

            os.makedirs(self.rundir)
            print('Created '+self.rundir)

        except OSError as e:

            if existscheck:

                if (e.errno == errno.EEXIST):
                    message = ('Directory ' + self.rundir + ' already exists.\n' +
                               'Continue anyway? (files could be overwritten)')
                    print(message)
                    go = uc.confirm(prompt=message,resp='y')
                    if (not go):
                        quit('Stopping.')
                else:
                    quit('Error creating directory.')
            else:

                pass


    def remove_directory(self, folder=None, confirm=True):

        """
            Remove all directory files created as part of this run instance

        """

        if folder != None:
            if self.rundir in folder:
                self.rmdir = folder
            else:
                self.rmdir = self.rundir + os.sep + folder
        else:
           self.rmdir = self.rundir

        if confirm:
            message = ('Are you sure you want to remove ' + self.rmdir + '\n' +
                        'and all sub folders and files (Ensure you have \n'
                        'copied all the data you need before deleting)' )
            print(message)
            go = uc.confirm(prompt=message,resp='y')
            if (not go):
                return #quit('Stopping.')

        #Remove directory
        print('Removing ' + self.rmdir)
        sh.rmtree(self.rmdir)

        return

    def prepare_mpiexec(self):

        if (self.platform == 'archer'):
            mpiexec = 'aprun'
        elif ("cx" in self.platform):
            mpiexec = 'mpiexec'
        elif (self.platform == 'local'):
            mpiexec = 'mpiexec'

        return mpiexec

    def cmd_includes_procs(self):
        if (self.platform == 'archer'):
            includes_procs = True
        elif ("cx" in self.platform):
            includes_procs = False
        elif (self.platform == 'local'):
            includes_procs = True

        return includes_procs

    def prepare_cmd_arguments(self):
        raise NotImplementedError

    def get_nprocs(self, *args, **kwargs):  
        raise NotImplementedError

    def prepare_cmd_string(self, executable, nprocs, extra_cmds=""):

        self.mpiexec = self.prepare_mpiexec()
        cmd_args = self.prepare_cmd_arguments()

        #Add call to python
        if (".py" in executable) and not ("python" in executable):
             executable = "python " + executable

        if self.cmd_includes_procs():
            cmd = (self.mpiexec + " -n " + str(nprocs) 
                   + " "  + executable + " " + cmd_args
                   + " " + extra_cmds)
        else:
            cmd = (self.mpiexec + " " + executable 
                   + " " + cmd_args + " " + extra_cmds)


        #If windows used, run Flowmol in linux subsystem
        print("Platform identified as ", sys.platform)
        if "linux" in sys.platform:
            pass
        elif "win" in sys.platform:
            cmd = 'bash -c "chmod +x ' + executable + ' ; ' + cmd + '"'
            print(cmd)
            

        return cmd

    def execute(self, blocking=False, nprocs=0, 
                print_output=False, out_to_file=True, 
                shell=False, extra_cmds=""):

        """
            Wrapper for execute_cx1, execute_local, and archer.

        """

        if ("cx" in self.platform or "archer" in self.platform):
            self.execute_pbs(blocking=blocking, extra_cmds=extra_cmds)
        else:
            self.execute_local(blocking=blocking, nprocs=nprocs, 
                               print_output=print_output,
                               out_to_file = out_to_file,
                               extra_cmds=extra_cmds, 
                               shell=shell)


    def execute_pbs(self, blocking=False, extra_cmds=""):

        """
            Submits a job from the directory specified  
            during instatiation of the object. 

        """ 
        nprocs = self.get_nprocs()
        cmd = self.prepare_cmd_string(self.executable, nprocs,
                                      extra_cmds=extra_cmds)

        job = PBSJob(self.rundir, self.jobname, nprocs, self.walltime, 
                    cmd, self.platform, queue=self.queue, 
                    extraargs=self.extraargs)

        # Submit the job
        job.submit(blocking=blocking, dryrun=self.dryrun)

    def output_generator(self, proc):
        for stdout_line in iter(proc.stdout.readline, ""):
            yield stdout_line 
        proc.stdout.close()
    

        
    def execute_local(self, blocking=False, nprocs=0,
                      print_output=False, out_to_file=True, 
                      shell=False, extra_cmds=""):

        """
            Runs an executable from the directory specified  
            during instatiation of the object. 
        """ 

        if (out_to_file and print_output):
            raise IOError("execute error, can't both print output and to file")

        # Store the number of processors required
        if nprocs==0:
            nprocs = self.get_nprocs()

        cmd = self.prepare_cmd_string(self.executable, nprocs,
                                      extra_cmds=extra_cmds)

        #Setup standard out and standard error files
        stdoutfile = self.rundir+self.outputfile
        stderrfile = self.rundir+self.outputfile+'_err'

        if (self.dryrun):
            print('DRYRUN -- no execution in ' + self.rundir + ' \nRun would be: ' + cmd)
        else:
            print(self.rundir + '    :    ' + cmd)
            if shell:
                split_cmdstg = cmd
            else:
                split_cmdstg = shlex.split(cmd)

            if print_output:
                self.proc = sp.Popen(split_cmdstg, cwd=self.rundir, stdin=None, 
                                     stdout=sp.PIPE, stderr=sp.STDOUT, 
                                     universal_newlines=True, shell=shell)
                for stdout_line in iter(self.proc.stdout.readline, ""):
                    lastline = stdout_line.replace("\n","")
                    print(lastline)
                self.proc.stdout.close()

            elif out_to_file:
                #Output is piped to files
                fstout = open(stdoutfile,'w')
                fsterr = open(stderrfile,'w')

                #Execute subprocess and create subprocess object
                self.proc = sp.Popen(split_cmdstg, cwd=self.rundir, stdin=None, 
                                     stdout=fstout, stderr=fsterr, shell=shell)
            else:
                self.CalledProcessError = sp.CalledProcessError
                self.proc = sp.Popen(split_cmdstg, cwd=self.rundir, stdin=None, 
                                     stdout=sp.PIPE, stderr=sp.PIPE, 
                                     universal_newlines=True, shell=shell)


            #If blocking, wait here
            if blocking:
                return_code = self.proc.wait()
                if return_code:
                    if not print_output:
                        with open(stderrfile, "r") as f:
                            error = f.read()
                        raise sp.CalledProcessError(return_code, cmd + "\n" + error)
                    else:
                        raise sp.CalledProcessError(return_code, cmd)

            if not print_output and out_to_file:
                fstout.close()
                fsterr.close()

        return

#    def execute_local(self, blocking=False, nprocs=0, 
#                      print_output=False, extra_cmds=""):

#        """
#            Runs an executable from the directory specified  
#            during instatiation of the object. 

#        """ 

#        # Store the number of processors required
#        if nprocs==0:
#            nprocs = self.get_nprocs()

#        cmd = self.prepare_cmd_string(self.executable, nprocs,
#                                      extra_cmds=extra_cmds)

#        #Setup standard out and standard error files
#        stdoutfile = self.rundir+self.outputfile
#        stderrfile = self.rundir+self.outputfile+'_err'

#        if (self.dryrun):
#            print('DRYRUN -- no execution in ' + self.rundir + ' \nRun would be: ' + cmd)
#        else:
#            print(self.rundir + '    :    ' + cmd)
#            split_cmdstg = shlex.split(cmd)

#            if print_output == True:
#                self.proc = sp.Popen(split_cmdstg, cwd=self.rundir, stdin=None, 
#                                     stdout=sp.PIPE, stderr=sp.STDOUT, 
#                                     universal_newlines=True)
#                for stdout_line in iter(self.proc.stdout.readline, ""):
#                    lastline = stdout_line.replace("\n","")
#                    if ("AssertionError" in lastline):
#                        raise AssertionError(lastline)
#                    else:
#                        print("Line=",lastline)

#                self.proc.stdout.close()

#                #If blocking, wait here
#                if blocking:
#                    return_code = self.proc.wait()

#            elif print_output == "catch_error":
#                try:
#                    output = sp.check_output(split_cmdstg, cwd=self.rundir, 
#                                             stdin=None, stderr=sp.STDOUT).decode()
#                    success = True 
#                except sp.CalledProcessError as e:
#                    output = e.output.decode()
#                    success = False

#                if (success == False):
#                    o = output.split("\n")
#                    for l in o:
#                        if ("AssertionError" in l):
#                            raise AssertionError(l)
#                    return_code = 1
#                else:
#                    return_code = 0

#            else:
#                #Output is piped to files
#                fstout = open(stdoutfile,'w')
#                fsterr = open(stderrfile,'w')

#                #Execute subprocess and create subprocess object
#                self.proc = sp.Popen(split_cmdstg, cwd=self.rundir, stdin=None, 
#                                     stdout=fstout, stderr=fsterr)

#                #If blocking, wait here
#                if blocking:
#                    return_code = self.proc.wait()

#            if print_output == False:
#                fstout.close()
#                fsterr.close()

#            if return_code:
#                if not print_output:
#                    with open(stderrfile, "r") as f:
#                        error = f.read()
#                    raise sp.CalledProcessError(return_code, cmd + "\n" + error)
#                else:
#                    raise sp.CalledProcessError(return_code, cmd)


#        if self.proc.poll() == None:
#            import time
#            time.wait(3)
#            self.proc.terminate()
#            self.proc.wait()

#        return return_code


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
                    if "Time" in line:
                        timetaken = line.split(';')[1]
                        finished_correctly = True
            if finished_correctly==False:
                raise SimIncompleteError 
            else:
                print('Simulation in directory ' + self.rundir + ' appears ' + 
                      'to have finished correctly in ' + timetaken + ' seconds,\n'
                       + 'the input file was ' + self.inputfile + '.')
        #If time taken output is not found, display the last 10 lines of error and output info 
        except SimIncompleteError:
            print('Simulation in directory ' + self.rundir + ', with input file\n'
                  + self.inputfile + ', appears to have failed:')
            with open(stderrfile,'r') as fileObj:
                print(' ==== Standard Error File for rundir ' + self.rundir + ' ==== ')
                lastlines = fileObj.readlines()[-10:]
                for line in lastlines:
                    print(line)
            with open(stdoutfile,'r') as fileObj:
                print(' ==== Standard output File ' + self.rundir + ' ==== ')
                lastlines = fileObj.readlines()[-10:]
                for line in lastlines:
                    print(line)
        except IOError:
            print('Unable to open stdoutfile' + stdoutfile + ' and stderrfile' 
                 + stderrfile + ' to check for simulation completion. ')

        # Run requested post processing scripts
        for entry in self.finishargs:

            key = entry[0]
            value = entry[1]

            if key == 'final_state':
                
                src = self.rundir + 'results' + os.sep + 'final_state'
                dst = self.rundir + value
                print('Moving ' + src + ' to ' + dst)
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
                print('Running gnuplot script ' + value +
                      ' with output ' + outfile)
                gnurun.wait()

                #Copy results back to calling directory and name by rundir
                sh.copy(self.rundir+outfile, outfile)
                valid_chars = "-_.() %s%s" % (string.ascii_letters, 
                                              string.digits)
                newname = ''.join((c for c in outfile+self.rundir 
                                   if c in valid_chars[6:]))
                os.rename(outfile, newname)
            
            if key == 'copy_resultsdir':
               
                src = self.rundir + 'results' + os.sep
                dst = self.rundir + value 
                print('Copying ' + src + ' to ' + dst) 
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
