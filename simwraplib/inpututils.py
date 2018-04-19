import string
import os
import numpy as np
from tempfile import mkstemp
from shutil import move
import shutil as sh
import subprocess as sp

from read_header import openfoam_HeaderData

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def reverse_readline(filename, buf_size=8192):
    """a generator that returns the lines of a file in reverse order"""
    with open(filename) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first 
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if len(lines[index]):
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment
#class changefile:
#    """Context manager for changing the current file"""
#    def __init__(self, oldfile, newfile=None):
#        self.oldfile = oldfile
#        if newfile == None:
#            self.newfile = oldfile + '.bak'
#        else:
#            self.newfile = newfile
#        #Create temp directory
#        self.fh, self.abs_path = mkstemp()

#    def __enter__(self):
#        open(self.abs_path,'w') as self.new_file
#        open(self.filename) as self.old_file

#    def __exit__(self, etype, value, traceback):
#        self.new_file.close()
#        self.old_file.close()
#        os.close(self.fh)
#        os.remove(self.filename)
#        #Move new file
#        move(self.abs_path, self.filename)


#    def generator():
#        for line in self.old_file:
#            self.new_file.write(line)
#            if not line:
#                continue
#            yield line



class InputMod:

    def __init__(self, filename):
        self.filename = filename
    
    def replace_input(self, keyword, keyvals):    
        raise NotImplementedError

class MDInputMod(InputMod):

    def __init__(self, filename):
        self.filename = filename
    
    def replace_input(self, keyword, keyvals):    

        """ 
            Replace N values underneath the first appearance of
            keyword with keyvals (length N)
            Input file of format:


            KEYWORD
            keyvals[0]
            keyvals[1]
            ...
            keyvals[-1]

        """

        found = False
        key_lno = 0 # Keyword linenumber

        for line in open(self.filename):
        
            key_lno += 1

            # Take into account keyword might be "turned off" by a
            # comment character before it
            if (line[0:len(keyword)]   == keyword or 
                line[1:len(keyword)+1] == keyword ): 

                # Mark the keyword as found 
                found = True

                # Ensure keyword is activated (i.e. not commented out)
                sedstr = ( "sed -i '" + str(key_lno) + "s/.*/" + keyword + 
                           "/' " + self.filename ) 
                os.system(sedstr)

                # Values start on next line
                val_lno = key_lno + 1

                if type(keyvals) is list:

                    for val in keyvals:

                        if (val != None):

                            sedstr = ( "sed -i '" + str(val_lno) + "s/.*/" + 
                                        str(val) + "/' " + self.filename ) 
                            os.system(sedstr)
                    
                        val_lno += 1

                else:

                    sedstr = ( "sed -i '" + str(val_lno) + "s/.*/" + 
                                str(keyvals) + "/' " + self.filename ) 
                    os.system(sedstr)

                # Stop looping through the file
                break
        
        if ( found == False ):

            with open(self.filename,'a') as f:
                f.write(keyword+'\n')
                for keyval in keyvals:
                    f.write(keyval+'\n')
    
            quit('Input string ' + keyword + 
                 ' not found, appended to file instead.')


class CFDInputMod(InputMod):
    
    def __init__(self,filename):
        InputMod.__init__(self,filename) 
  
    def replace_input(self, keyword, keyval):
         
        """ 
            Replace value before all appearances of
            keyword with keyval 

        """
        f = open(self.filename,'r')
        fout = open(self.filename+'.tmp','w')
        
        lines = f.readlines()
        keywordfound = False
        for line in lines:

            try:
                name = line.split()[1]
            except IndexError:
                name = None

            if (name == keyword):
                keywordfound = True
                value = line.split()[0]
                fout.write(line.replace(value,keyval))
            else:
                fout.write(line)

        if (not keywordfound):
            print('Input string '+keyword+' not found.')
        sh.move(self.filename+'.tmp',self.filename) 


class OpenFOAMInputMod(InputMod):

    def __init__(self, fdir):
        self.fdir = fdir
        self.headerObj = openfoam_HeaderData(fdir)
        self.HD = self.headerObj.headerDict

    #OpenFOAM input has no consistent format
    #but various patterns such as:
    # 1) Keyword with data to change in () brackets on next two lines
    # 2) Keyword with data to change in {} brackets on next two lines
    # 3) Keyword with data to change as number following
    # 4) Keyword with data to change in brackets following

#    def replace_hex(line, new_file, keyvals):
#        newlinebase = line #line.split("'")[1]
#        cells = str(keyvals[0]) + " " + str(keyvals[1]) + " " + str(keyvals[2])
#        elements = newlinebase.replace('(',')').split(")")
#        elements[3] = cells
#        brackets = ["(", ")"]
#        newline = ''.join([str(e) + brackets[i%2] for i,e in enumerate(elements)])[:-1]
#        #print(newlinebase, newline, newline==newlinebase)
#        new_file.write(newline)

##    def replace_proces(line, new_file, keyvals):


#    def replace_domain(line, new_file, keyvals):
#        xo, yo, zo, Lx, Ly, Lz = keyvals
#        newvertices = (
#        "(\n" + 
#        "    (" + str(xo) + " " + str(yo) + " " + str(zo) + ")\n"
#        "    (" + str(Lx) + " " + str(yo) + " " + str(zo) + ")\n"
#        "    (" + str(Lx) + " " + str(Ly) + " " + str(zo) + ")\n"
#        "    (" + str(xo) + " " + str(Ly) + " " + str(zo) + ")\n"
#        "    (" + str(xo) + " " + str(yo) + " " + str(Lz) + ")\n"
#        "    (" + str(Lx) + " " + str(yo) + " " + str(Lz) + ")\n"
#        "    (" + str(Lx) + " " + str(Ly) + " " + str(Lz) + ")\n"
#        "    (" + str(xo) + " " + str(Ly) + " " + str(Lz) + ")\n"
#        ");\n")
#        new_file.write(newvertices)

    def replace_input(self, keyword, keyvals):    

        """ 
            Replace OpenFOAM

            Currently support  'cell', 'domainsize', 
            'origin' and 'process' keywords with list of three
            values for each. The user can also specify the full
            OpenFOAM format in the slightly cumbersome but completely 
            consistent form of nested dicts/lists, for example to set cells
            keyword = "blockMeshDict"
            keyvals = {"blocks":{"hex":["keep",[8,8,8],"keep","keep"]}}
            where the "keep" keyword says to skip replacing values.
            also, to set processors
            keyword = ["decomposeParDict", "decomposeParDict"]
            keyvals = [{"numberOfSubdomains":8}, 
                       {"numberOfSubdomains":{simpleCoeffs:{"n":[2,2,2]}}}]

        """

        #Full openfoam form
        if type(keyvals) is dict:
            for k, v in keyvals.items():
                self.HD[keyword][k] = v
            #quit()
            self.headerObj.header_changer(self.HD[keyword])

        #Pre defined options
        else:
            #Otherwise we support a few easy options
            HD = self.HD
            headerObj = self.headerObj
            #Number of cells
            if ("cell" in keyword.lower()):
                assert len(keyvals) == 3
                HD['blockMeshDict']['blocks']['hex'][1] = keyvals
                headerObj.header_changer(HD['blockMeshDict'])
            #Number of processes
            elif ("process" in keyword.lower()):
                assert len(keyvals) == 3            
                npx, npy, npz = keyvals
                HD['decomposeParDict']["numberOfSubdomains"] = npx*npy*npz
                HD['decomposeParDict']["simpleCoeffs"]["n"][0] = [npx, npy, npz]
                headerObj.header_changer(HD['decomposeParDict'])
            elif (("origin" in keyword.lower()) or 
                ("domainsize" in keyword.lower())):
                if ("domainsize" in keyword.lower()):
                    assert len(keyvals) == 3
                    xo, yo, zo = HD['blockMeshDict']['vertices'][0]
                    Lx, Ly, Lz = keyvals
                elif ("origin" in keyword.lower()):
                    assert len(keyvals) == 3
                    xo, yo, zo = keyvals
                    Lx, Ly, Lz = HD['blockMeshDict']['vertices'][6]

                newvertices =[[xo, yo, zo],
                              [Lx, yo, zo],
                              [Lx, Ly, zo],
                              [xo, Ly, zo],
                              [xo, yo, Lz],
                              [Lx, yo, Lz],
                              [Lx, Ly, Lz],
                              [xo, Ly, Lz]]
                HD['blockMeshDict']['vertices'] = newvertices
                headerObj.header_changer(HD['blockMeshDict'])
            else:
                print("Only 'cell', 'domainsize', 'origin' and 'process' keywords currently supported")
                raise NotImplementedError


        #Trigger rebuild of code
        with cd(self.fdir):
            clean = sp.check_output("python clean.py -f", shell=True)
            blockMesh = sp.Popen("blockMesh", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            out, err = blockMesh.communicate()
            if "not found" in err:
                print("WARNING -- blockMesh not found, have you called SOURCEME.sh in OpenFOAM APP")
            decomposeParDict = sp.Popen("decomposePar", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            out, err = decomposeParDict.communicate()
            if "not found" in err:
                print("WARNING -- decomposePar not found, have you called SOURCEME.sh in OpenFOAM APP")

class LammpsInputMod(InputMod):


    def __init__(self, filename):
        self.filename = filename

    def replace_input(self, keyword, keyvals):    

        """ 
            Replace Lammps
        """

        replacefile = self.filename + ".new"
        sh.copy(self.filename, self.filename+".bak")
        with open(replacefile,'w') as new_file:
            with open(self.filename) as old_file:
                for line in old_file:
                    l = line.strip().replace("\t","")
                    ls = " ".join(l.split())
                    if keyword in ls:
                        #Replace line which contains keyword with values
                        nl = keyword + "   "
                        nl += " ".join([str(v) for v in keyvals])
                        new_file.write(nl+"\n")
                    else:
                        new_file.write(line)

        #Replace original file
        sh.copy(replacefile, self.filename)

#List of Dictonary classes with added routines to add and multiple inputs
class InputList(list):
    def __init__(self,*arg,**kw):
        super(InputList, self).__init__(*arg, **kw)

        self.valid_chars = "-.() _%s%s" % (string.ascii_letters, string.digits)

    #Define Addition operation as elementwise addition
    def __add__(self, x):

        if (type(x) == InputDict):
            Listx = x.expand()
        elif (type(x) == InputList):
            Listx = x
        else:
            raise TypeError("Unsupported type " + str(type(x))  
                            + " for input addition" + 
                            " -- must be InputList or InputDict type")

        returnlist = InputList()
        ziplist = zip(self,Listx)
        for entry in ziplist:
            tempdict = {}
            for dic in entry:
                tempdict.update(dic)
            returnlist.append(tempdict)

        return returnlist

    __radd__=__add__

    #Define multiplication operation as all permutations of inputs
    def __mul__(self, x):

        if (type(x) == InputDict):
            Listx = x.expand()  
        elif (type(x) == InputList):
            Listx = x
        else:
            raise TypeError("Unsupported type " + str(type(x))  
                            + " for input multiplication" + 
                            " -- must be InputList or InputDict type")

        returnlist = InputList()
        for entry1 in self:
            for entry2 in Listx:
                newdict = {}
                newdict.update(entry1)
                newdict.update(entry2)
                returnlist.append(newdict)

        return returnlist

    __rmul__=__mul__

    #Define Addition operation as elementwise addition
    def zip_inputs(self, x):

        returnlist = self + x

        return returnlist

    #Generate all permutations of inputs and return filenames
    def outer_product_inputs(self,x):

        returnlist = self*x

        return returnlist

    def filenames(self, seperator=""):

        #Generate list containing filenames
        filenames = []
        for name in self:
            filename = ''
            for key, value in name.items():
                if type(value) is float:
                    value = np.round(value,2)
                if type(value) is int:
                    value = value

                # Combine key and value with invalid characters removed
                kvstr = key
                if type(value) is list:
                    for v in value:
                        kvstr += seperator + str(v)
                else:
                    kvstr += seperator + str(value)
                kvstr = kvstr.replace('.','p')
                filename = filename + (''.join(c for c in kvstr 
                                       if c in (self.valid_chars[6:] + seperator)))

            filenames.append(filename)

            #print(name,filename)


        #First remove any invalid characters
        #filenames=[(''.join(c for c in str(name.items()) 
        #                  if c in self.valid_chars[6:]))
        #                  for name in self]
         
        return filenames

#Dictonary class with added routines to add and multiple inputs
class InputDict(dict):
    def __init__(self,*arg,**kw):
        super(InputDict, self).__init__(*arg, **kw)

    #Expand InputDict with multiple values per entry into InputList
    def expand(self):

        expansion = self.values()[0]
        returnlist = InputList({self.keys()[0]:e} for e in expansion)
        
        return returnlist       

    #Wrapper to convert InputDict to InputList then add
    def __add__(self, x):

        # Convert to lists
        templist = self.expand()
        returnlist = templist + x

        return returnlist

    __radd__=__add__

    #Wrapper to convert InputDict to InputList then multiply
    def __mul__(self, x):

        # Convert to lists
        templist = self.expand()
        returnlist = templist * x

        return returnlist

    __rmul__=__mul__
