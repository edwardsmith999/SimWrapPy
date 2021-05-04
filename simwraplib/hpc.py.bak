#! /usr/bin/env python
import time
import os
import math as maths
import subprocess as sp

from simwraplib.platform import get_platform


class PBSJob:

    def __init__(self,
                 rundir,
                 jobname,
                 nproc,
                 walltime,
                 exec_cmd,
                 platform,
                 queue='',
                 extraargs={}):

        # Store absolute run directory so we can move around after submission
        absrundir = os.path.abspath(rundir)

        # Get platform if not specified
        if (platform == None):
            self.platform = get_platform()
        else:
            self.platform = platform

        # Create CXJob object based on the platform
        if (self.platform == 'cx1'):
            cpuspernode = 8
        elif (self.platform == 'cx2'):
            cpuspernode = 12
        elif (self.platform == 'archer'):
            cpuspernode = 24
        elif (self.platform == 'local'):
            errstr = 'Apparently local job trying to be run using hpc script \n'
            errstr += 'or unrecognised platform/environment in PBSJob'
            raise EnvironmentError(errstr)
        else:
            raise EnvironmentError('Unrecognised platform in PBSJob')


        # Calculate number of nodes required
        select = int(maths.ceil(float(nproc)/float(cpuspernode)))

        script = "#!/bin/bash \n"
        script += "#PBS -N {} \n".format(jobname)
        script += "#PBS -l walltime={} \n".format(walltime)
        script += "#PBS -l select={}:ncpus={} \n".format(select, cpuspernode)
        script += "#PBS -q {} \n".format(queue)

        #Look for PBS keywords in extraargs
        for k, v in extraargs.items():
            if ("PBS" in k):
                script += "#PBS " + [str(i) for i in v] + "\n"

        script += "\n"

        # Platform specific parts of script
        if ('cx' in platform):

            script += 'module load intel-suite\n'
            script += 'module load mpi\n\n\n'

        elif (platform == 'archer'):
                
            #Create new script to replace first line 
            script = "#!/bin/bash --login \n" + "\n".join(script.split("\n")[1:])

            script += "export OMP_NUM_THREADS=1\n"

        else:
            
            quit('Unrecognised platform ' + platform + ' in CXJob')

        #Look for other keywords in extraargs
        for k, v in extraargs.items():
            if ("qscript" in k):
                script += v + "\n"

        script += 'cd ' + absrundir + '\n\n'
        script += 'date\n\n'
        script += exec_cmd + '\n\n'
        script += 'date\n'

        # Store variables
        self.script = script

        # CX systems return error if jobname longer than 13 characters
        if (len(jobname) > 13):
            self.jobname = jobname[:13]
            print("Warning, jobname " + jobname + " longer than max of 13, truncating")
        else:
            self.jobname = jobname 

        self.rundir = rundir

        return

    def submit(self, blocking=False, dryrun=False):

        # Open job submission file and write script to it
        job_file = "qscript" #self.jobname
        fobj = open(self.rundir+job_file,'w')
        fobj.write(self.script)
        fobj.close()

        if dryrun:
            print("This is a dryrun -- otherwise would submit " + self.rundir + job_file)
            return

        # Submit script and store the submission ID
        sub_id = sp.Popen(["qsub", job_file], cwd=self.rundir,
                          stdout=sp.PIPE).communicate()[0]

        sub_id = sub_id.strip()

        # Alert user of job submission
        print('Submitted ' + self.rundir + job_file + ': ' + sub_id)
      
        # If blocking, check qstat until sub_id no longer appears
        if (blocking):

            while True:

                qstat = sp.Popen(["qstat"],stdout=sp.PIPE).communicate()[0]
                if (sub_id not in qstat):
                    break 

                # Don't flood cx1/2 with qstat requests
                time.sleep(100)

        return


#class CXJob(PBSJob):

#    cpuspernode = 8

#    def __init__(self,
#                 rundir,
#                 jobname,
#                 nproc,
#                 walltime,
#                 exec_cmd,
#                 platform=None,
#                 queue='',
#                 icib='true'):

#class archerJob(PBSJob):

#    cpuspernode = 24

#    def __init__(self,
#                 rundir,
#                 jobname,
#                 nproc,
#                 walltime,
#                 exec_cmd,
#                 platform=None,
#                 queue='',
#                 icib='true'):


