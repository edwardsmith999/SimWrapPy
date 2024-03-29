
import string
import os
import numpy as np
from tempfile import mkstemp
from shutil import move
import shutil as sh
import subprocess as sp

from .read_header import openfoam_HeaderData

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

import re
import shutil
from tempfile import mkstemp


def sed(pattern, replace, source, dest=None, count=0):
    """Reads a source file and writes the destination file.

    In each line, replaces pattern with replace.

    Args:
        pattern (str): pattern to match (can be re.pattern)
        replace (str): replacement str
        source  (str): input filename
        count (int): number of occurrences to replace
        dest (str):   destination filename, if not given, source will be over written.        
    """

    fin = open(source, 'r')
    num_replaced = count

    if dest:
        fout = open(dest, 'w')
    else:
        fd, name = mkstemp()
        fout = open(name, 'w')

    for line in fin:
        out = re.sub(pattern, replace, line)
        fout.write(out)

        if out != line:
            num_replaced += 1
        if count and num_replaced > count:
            break
    try:
        fout.writelines(fin.readlines())
    except Exception as E:
        raise E

    fin.close()
    fout.close()

    if not dest:
        sh.move(name, source) 


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


def check_replace_line(line, keyword, keyvals):

    l = line.strip().replace("\t","")
    ls = " ".join(l.split())
    kw = " ".join(keyword.split())
    if kw in ls:
        indx = ls.find(kw)
        if  indx == 0:
            #Replace line which contains keyword with values
            nl = keyword + "   "
        else:
            nl = ls[:indx] + " " + keyword + " "
        if type(keyvals) is list:
            nl += " ".join([str(v) for v in keyvals])
        elif type(keyvals) is str:
            nl += keyvals
        elif type(keyvals) in (int, float, np.float64):
            nl += str(keyvals)
        else:
            raise TypeError("Unsupported keyvals type ", type(keyvals))
        return nl+"\n", True
    else:
        return line, False

class InputMod(object):

    def __init__(self, filename):
        self.filename = filename
    
    def replace_input(self, keyword, keyvals):    
        raise NotImplementedError

class ScriptMod(object):

    def __init__(self, filename):
        self.filename = filename
    
    def replace_input(self, keyword, keyvals):    

        #We only want to replace at most one time
        found = False
        replacefile = self.filename + ".bak"
        #sh.copy(self.filename, self.filename+".bak")
        with open(replacefile,'w') as new_file:
            with open(self.filename) as old_file:
                if type(keyword) is int:
                    #Replace line number in Python script
                    #We add one as line numbers start from one
                    for no, line in enumerate(old_file):
                        if no+1 == keyword:
                            new_file.write(keyvals+"\n")
                        else:
                            new_file.write(line)
                elif type(keyword) is str:
                    for line in old_file:                      
                        if not found:
                            l, found = check_replace_line(line, keyword, keyvals)
                        else:
                            l = line
                        new_file.write(l)

        #Replace original file
        sh.copy(replacefile, self.filename)

class KeywordInputMod(InputMod):

    def __init__(self, filename):
        super(KeywordInputMod, self).__init__(filename)

    def read_inputs(self, keyword, nkeyvals=-1):
        """ 
            Read N values underneath the first appearance of
            keyword with keyvals (length N)
            Input file of format:


            KEYWORD
            keyvals[0]
            keyvals[1]
            ...
            keyvals[-1]

        """

        found = False
        nvals = nkeyvals
        vals = []
        for line in open(self.filename):
            if found:
                if (nkeyvals == -1):
                    if line in ['\n', '\r\n'] or line[0] == "#":
                        break
                    else:
                        vals.append(line.strip().replace("\n", ""))
                elif (nvals > 0):
                    vals.append(line.strip().replace("\n", ""))
                    #print(line)
                    nvals -= 1
                elif (nvals == 0):
                    break

            # Take into account keyword might be "turned off" by a
            # comment character before it
            elif (line[0:len(keyword)]   == keyword or 
                  line[1:len(keyword)+1] == keyword ): 

                # Mark the keyword as found 
                found = True

        return vals
                

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
        sh.copy(self.filename, self.filename+".bak") 

        #fd, tempfile = mkstemp()
        tempfile = self.filename + ".temp"
        fout = open(tempfile, 'w')
        #skipcount = 0

        with open(self.filename) as fin:
            for line in fin:
                # Take into account keyword might be "turned off" by a
                # comment character before it
                if ((line[0:len(keyword)]   == keyword or 
                     line[1:len(keyword)+1] == keyword)  
                     and not found): 

                    # Mark the keyword as found 
                    found = True

                    # Ensure keyword is activated (i.e. not commented out)
                    fout.write(keyword+"\n")
                    print("writing = ", keyword)

                    # Values start on next line
                    if type(keyvals) is list:
                        for val in keyvals:
                            try:
                                nl = next(fin)
                            except StopIteration:
                                nl = ""
                            if (val != None):
                                fout.write(str(val) + "\n")
                                print("Replacing ", nl.replace("\n",""), "with", str(val))
                            else:
                                print("NOT replacing ", nl.replace("\n",""))
                                fout.write(nl)
                                #skipcount += 1
                    else:
                        fout.write(str(val))

                #elif skipcount == 0:
                else:
                    #print(line, keyword, keyvals, found)
                    fout.write(line)
                #else:
                    #print("Skipping", line, skipcount)
                    #skipcount -= 1

        #Close new file and replace old one
        fout.close()
        sh.move(tempfile, self.filename)

        #Append to file if not found
        if ( found == False ):
            with open(self.filename,'a') as f:
                f.write(keyword+'\n')
                for keyval in keyvals:
                    f.write(str(keyval)+'\n')

            print('Input string ' + keyword + 
                  ' not found, appended to file instead.')


    def replace_input_sed(self, keyword, keyvals):    

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
                print("sed = ", keyword, keyvals, sedstr)
                os.system(sedstr)

                # Values start on next line
                val_lno = key_lno + 1

                if type(keyvals) is list:

                    for val in keyvals:

                        if (val != None):

                            sedstr = ( "sed -i '" + str(val_lno) + "s/.*/" + 
                                        str(val) + "/' " + self.filename ) 
                            print("sed = ", keyword, keyvals, sedstr)

                            os.system(sedstr)
                    
                        val_lno += 1

                else:

                    sedstr = ( "sed -i '" + str(val_lno) + "s/.*/" + 
                                str(keyvals) + "/' " + self.filename ) 
                    print("sed = ", keyword, keyvals, sedstr)

                    os.system(sedstr)

                # Stop looping through the file
                break
        
        if ( found == False ):

            print((keyword, keyvals))
            with open(self.filename,'a') as f:
                f.write(keyword+'\n')
                for keyval in keyvals:
                    f.write(str(keyval)+'\n')
    
            print('Input string ' + keyword + 
                  ' not found, appended to file instead.')

class MDInputMod(KeywordInputMod):
    def __init__(self,filename):
        super(MDInputMod, self).__init__(filename)

class CommentedInputMod(InputMod):
    
    def __init__(self, filename):
        super(CommentedInputMod, self).__init__(filename)
  
    def replace_input(self, keyword, keyval):
         
        """ 
            Replace value before all appearances of
            keyword with keyval. For example if 
            you have a file with valeus and comments as follows:

            500000              !Number of computational steps
            100                 !Frequency of ouput plots
            4                   !Number of cells in Domain in x - nx
            8                   !Number of cells in Domain in y - ny
            4                   !DUMMY Number of cells in Domain in z - nz
            47.6220315590460    !Domain size in x - lx
            46.98707113825872   !Domain size in y - ly
            47.6220315590460    !DUMMY Domain size in z - lz
            0.005               !Time step delta t
            1.6                 !Viscosity
            0.8                 !Density

            you can use keyword="Viscosity" and change this keyval

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
            print(('Input string '+keyword+' not found.'))
        sh.move(self.filename+'.tmp',self.filename) 

class CFDInputMod(CommentedInputMod):
    def __init__(self,filename):
        super(CFDInputMod, self).__init__(filename)


class OpenFOAMInputMod(InputMod):

    def __init__(self, fdir):
        self.fdir = fdir
        self.headerObj = openfoam_HeaderData(fdir)
        self.HD = self.headerObj.headerDict

    def replace_input(self, keyword, keyvals):    

        """ 
            Replace OpenFOAM

            A few shortcut keywords and a comprehensive underlying 
            way of exploring changing of inputs.

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
            for k, v in list(keyvals.items()):
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
            blockMesh = sp.Popen("blockMesh", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, encoding='utf8')
            out, err = blockMesh.communicate()
            if "not found" in err:
                print("WARNING -- blockMesh not found, have you called SOURCEME.sh in OpenFOAM APP")
            decomposeParDict = sp.Popen("decomposePar", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, encoding='utf8')
            out, err = decomposeParDict.communicate()
            if "not found" in err:
                print("WARNING -- decomposePar not found, have you called SOURCEME.sh in OpenFOAM APP")


class LineInputMod(InputMod):

    def __init__(self, filename):
        self.filename = filename

    def replace_input(self, keyword, keyvals):    

        """ 
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
        
        """

        replacefile = self.filename + ".new"
        sh.copy(self.filename, self.filename+".bak")
        with open(replacefile,'w') as new_file:
            with open(self.filename) as old_file:
                for line in old_file:
                    l, found = check_replace_line(line, keyword, keyvals)
                    new_file.write(l)

        #Replace original file
        sh.copy(replacefile, self.filename)


class LammpsInputMod(LineInputMod):
    def __init__(self, filename):
        super(LammpsInputMod, self).__init__(filename)

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
        ziplist = list(zip(self,Listx))
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
            for key, value in list(name.items()):
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

        expansion = list(self.values())[0]
        returnlist = InputList({list(self.keys())[0]:e} for e in expansion)
        
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
