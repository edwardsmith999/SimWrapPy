import multiprocessing
import subprocess as sp

from platform import get_platform
from thread import Thread
from semaphores import DummySemaphore, Multiphore

class Study:

    def __init__(self, threadlist, maxproc=None, studyfolder=None):

        """
            A single study of multiple MDThreads, each carrying
            the responsibility of executing a series of sequential
            MDRun objects. 
 
            Constructor arguments:
            
                threadlist - a list of runlists. Each runlist contains a
                             series of Run objects to be executed 
                             sequentially
                
                maxproc - maximum number of licenses the semaphore may
                          release at once. 

                studyfolder - Group all runs into a study folder wih 
                              all copied src and executable setup files 
                              in run.setup checked and if the same,
                              copied only once for the study. 

        """

        self.threadlist = threadlist
        self.maxproc = maxproc
        #Get platform and check if different from specified in run objects
        self.platform = get_platform()
        first_run = True
        for thread in threadlist:
            for run in thread:
                if (self.platform != run.platform):
                    print("Platform inconsistent in run", run.platform, self.platform)
                self.platform = run.platform
                if studyfolder is not None:
                    topdir = run.rundir.split("/")[-1]
                    if topdir is "":
                        topdir = run.rundir.split("/")[-2]
                        run.rundir= (  "/".join(run.rundir.split("/")[:-2]) 
                                     + "/" + studyfolder + "/" + topdir + "/")
                    else:
                        run.rundir= (  "/".join(run.rundir.split("/")[:-1])
                                     + "/" + studyfolder + "/" + topdir + "/")
                    if not first_run:
                        run.minimalcopy = True
                    else:
                        first_run = False

        #Get semaphore is possible, otherwise use dummy routine
        if (get_platform() == 'local'):

            # Get number of cpus on computer if not specified
            if maxproc == None:
                print("Maximum number concurrent processors not specified, " +
                      "attempting to use total number of CPUs...")
                try:
                    ncpus = multiprocessing.cpu_count()
                except NotImplementedError:
                    raise

            self.semaphore = Multiphore(maxproc)

        else:

            print('Semaphore not available, creating dummy instead.')
            self.semaphore = DummySemaphore()

        self.threads = []
        for runlist in threadlist:
            thread = Thread(self.semaphore, runlist)
            self.threads.append(thread)
            #thread.start()

        #The jobs should not be run in the constructor surely?!
        self.run()

        #for thread in self.threads:
        #    thread.join()

    def run(self):

        for thread in self.threads:
            thread.start()

        for thread in self.threads:
            thread.join()
