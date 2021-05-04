import glob
import re
import os 
import shutil as sh

class openfoam_HeaderData:

    """
        A recursive reader and changer for Openfoam
        input system. Pyfoam does this but is massive
        so easier to just provide a minimal script.
        How well this work depends on the files:
        OpenFOAM input has no consistent format
        but various patterns such as:
         1) Keyword with data to change in () brackets on next two lines
         2) Keyword with data to change in {} brackets on next two lines
         3) Keyword with data to change as number following
         4) Keyword with data to change in brackets following
         5) Keyword with units in [] and then data to change following
        As a result, this is a horrible bit of code below...
    """

    def __init__(self, fdir, readfields=True):

        if (fdir[-1] != '/'): fdir += '/'
        self.fdir = fdir
        headerfiles = self.get_header_files()
                      #["blockMeshDict", "transportProperties", "controlDict", 
                      #  "environmentalProperties", "decomposeParDict"]
        fieldfiles = self.get_field_files()
        
        if readfields:
            fieldfiles = self.get_field_files()
            readfiles = headerfiles + fieldfiles
        else:
            readfiles = headerfiles

        headerDict = {}
        for filename in readfiles:
            if os.path.isfile(filename):
                with open(filename) as f:
                    lines = self.lines_generator_strip(f)
                    header = self.header_parser(lines)
                    header["fname"] = filename
                headerDict[filename.split("/")[-1]] = header
        self.headerDict = headerDict

    def get_header_files(self):
        paths = [self.fdir + f for f in ['constant', 'system']]
        filenames = []
        for path in paths:
            files = glob.glob(path + "/*")
            for filename in files:
                filenames.append(filename)

        filenames.append(self.fdir + "constant/polyMesh/blockMeshDict")

        return filenames

    def get_field_files(self):

        path = self.fdir + "0/"
        files = glob.glob(path + "/*")
        filenames = []
        for filename in files:
            try:
                with open(filename) as f:
                    for line in f:
                        if "class" in line:
                            fname = filename.split("/")[-1]
                            if "volScalarField" in line:
                                filenames.append(filename)
                            elif "volVectorField":
                                filenames.append(filename)
                            elif "volSymmTensorField":
                                filenames.append(filename)
                            else:
                                continue
            except IOError:
                pass

        return filenames

    def lines_generator(self, lines):
        for line in lines:
            if not line:
                continue
            yield line

    def lines_generator_strip(self, lines):
        for line in lines:
            line = line.strip()
            if not line:
                continue
            yield line

    def stringtolist(self, s):
        v = s.replace("(","").replace(")","").split()
        r = []
        for i in v:
            try:
                r.append(int(i))
            except ValueError:
                try:
                    r.append(float(i))
                except ValueError:
                    r.append(i)
        return r

    def header_parser(self, lines):

        """
            Recursive header parser which
            builds up a dictonary of input files
        """
        ft = True
        Out = {}
        prevline = ""
        for line in lines:

            #Skip comments
            if line[0:2] == "/*":
                break_next = False
                for line in lines:
                    if break_next:
                        break
                    if '\*' in line:
                        break_next=True
            if "//" in line:
                continue

            #Split line into list
            split = line.split() 

            #One elemnt means we will go down to another level of nesting
            if len(split) == 1:
                if line == '{':
                    Out[prevline] = self.header_parser(lines)
                elif line == '(':
                    Out[prevline] = self.header_parser(lines)
                elif line == ');':
                    return Out
                elif line == '}':
                    return Out
                else:
                    Out[line] = None
            #If ends with a semi-colon then we define a value
            elif len(split) == 2:
                if line[-1] == ";":
                    key, value = split
                    Out[key] = value.strip(';')
                else:
                    print("Error, two values not a statement", line)
            #Otherwise we have to parse as needed
            elif len(split) > 2:
                key = split[0]
                if ("[" in line):
                    indx = line.find("]")
                    afterunits = line[indx+1:].replace(";","")
                    Out[key] = self.stringtolist(afterunits)
                elif ("(" in key):
                    if ft:
                        ft = False
                        Out = []
                    Out.append(self.stringtolist(line))
                else:
                    #As we have a key, we assume multiple brackets on line
                    indx = line.find(key)
                    remainingline = line[indx+len(key):]
                    rsplit = re.findall("\((.*?)\)", remainingline)
                    #rsplit = remainingline.replace("(",")").split(")")[:-1]
                    vals = []
                    for s in rsplit:
                        vals.append(self.stringtolist(s))
                    Out[key] = vals

            if line[-1] == ");":
                return Out

            if line[-1] == "}":
                return Out

            prevline = line

        return Out

    def find_nth(self, haystack, needle, n):
        start = haystack.find(needle)
        while start >= 0 and n > 1:
            start = haystack.find(needle, start+len(needle))
            n -= 1
        return start

    def header_changer(self, ChangeDict):

        #Get file name from dictonary
        try:
            fname = ChangeDict["fname"]
            sh.copy(fname, fname+".bak")
            #Create temp file
            with open(fname+"new",'w+') as new_file:
                with open(fname) as old_file:
                    lines = self.lines_generator(old_file)
                    self.header_change(lines, new_file, ChangeDict)

        except KeyError:
            raise KeyError("fname not found in dictonary, specify a file dictonary")

        sh.move(fname+"new", fname)

    def header_change(self, lines, new_file, ChangeDict):
        ft = True
        prevline = ""
        Out = {}
        for l in lines:
            if l == "\n":
                new_file.write(l)
                continue

            line = l.strip()

            try:
                #Skip comments
                if line[0:2] == "/*":
                    new_file.write(l)
                    break_next = False
                    for l in lines:
                        line = l.strip()
                        if break_next:
                            break
                        new_file.write(l)
                        if '\*' in line:
                            break_next=True
                if "//" in line:
                    new_file.write(l)
                    continue

                #Split line into list
                split = line.split()

                #One element means we will go up or down a level of nesting
                if len(split) == 1:
                    #Down a level
                    if line == '{':
                        new_file.write(l)
                        Out[prevline] = self.header_change(lines, new_file, ChangeDict[prevline])
                    #Down a level
                    elif line == '(':
                        new_file.write(l)
                        Out[prevline] = self.header_change(lines, new_file, ChangeDict[prevline])
                    #Up a level
                    elif line == ');':
                        new_file.write(l)
                        return Out
                    #Up a level
                    elif line == '}':
                        new_file.write(l)
                        return Out
                    #Otherwise just write this value
                    else:
                        new_file.write(l)
                        Out[line] = None

                #If ends with a semi-colon then we define a value
                elif len(split) == 2:
                    if line[-1] == ";":
                        key, value = split
                        Out[key] = value.strip(';')
                        if (ChangeDict[key] == Out[key] or ChangeDict[key]=="keep"):
                            new_file.write(l)
                        else:
                            new_file.write(key + "    " + str(ChangeDict[key]) + ";\n")
                    else:
                        print("Error, two values not a statement", line)
                #Otherwise we have to parse as needed
                elif len(split) > 2:
                    key = split[0]
                    #Read units
                    if ("[" in line):
                        indx = line.find("]")
                        afterunits = line[indx+1:].replace(";","")
                        Out[key] = self.stringtolist(afterunits)
                        if (ChangeDict[key] == Out[key] or ChangeDict[key]=="keep"):
                            new_file.write(l)
                        else:
                            indx = l.find("]")
                            nl = l[:indx]
                            if type(ChangeDict[key] is list):
                                nl += " ("
                                nl += " ".join(str(e) for e in ChangeDict[key])
                                nl += ")"
                            else:
                                nl += " " + str(ChangeDict[key])
                            new_file.write(nl+";\n")
                    #Read array of value
                    elif ("(" in key):
                        if ft:
                            ft = False
                            Out = []
                            i = 0
                        Out.append(self.stringtolist(line))
                        if (ChangeDict[i] == Out[i] or ChangeDict[i]=="keep"):
                            new_file.write(l)
                            i += 1
                        else:
                            indxl = l.find("(")
                            nl = l[:indxl+1] 
                            nl += " ".join(str(e) for e in ChangeDict[i])
                            nl += ")"
                            new_file.write(nl+"\n")
                            #print(i, l, nl, ChangeDict[i])
                            i += 1
                    else:
                        #As we have a key, we assume multiple brackets on line
                        indx = line.find(key)
                        remainingline = line[indx+len(key):]
                        rsplit = re.findall("\((.*?)\)", remainingline)
                        vals = []
                        for s in rsplit:
                            vals.append(self.stringtolist(s))
                        Out[key] = vals
                        if (ChangeDict[key] == Out[key] or ChangeDict[key]=="keep"):
                            new_file.write(l)
                        else:
                            indxl = self.find_nth(l, "(", 1)
                            nl = l[:indxl]
                            for i, lst in enumerate(ChangeDict[key]):
                                nl += "("
                                nl += " ".join(str(e) for e in lst)
                                indxr = self.find_nth(l, ")", i+1)
                                indxl = self.find_nth(l, "(", i+2)
                                nl += l[indxr:indxl]

                            #print(key, l, ChangeDict[key], nl)
                            new_file.write(nl+"\n")

                try:
                    if line[-1] == ");":
                        new_file.write(l)
                        return Out

                    if line[-1] == "}":
                        new_file.write(l)
                        return Out
                except IndexError:
                    new_file.write(line)

                prevline = line

            except KeyError:
                if key == "keep":
                    new_file.write(line)
                else:
                    print(key, ChangeDict)
            except:
                raise
                new_file.write(l)

        return Out

if __name__ == "__main__":

    #Load header data from fdir
    fdir = "/home/es205/codes/cpl_granlammmps/OpenFOAM-3.0.1_LAMMPS-dev/OpenFOAM-3.0.1_coupled/runs/Couette_Gran/openfoam"
    headerObj = openfoam_HeaderData(fdir)
    HD = headerObj.headerDict

    # ---------------------------------
    # Change number of cells
    # ---------------------------------

    #Change number of cells in y to 12
    HD['blockMeshDict']['blocks']['hex'][1][1] = 12

    #Change vertices to new Lx, Ly and Lz values
    xo=0.; yo=0.; zo=0; Lx=2.; Ly=2.; Lz=2.
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

    # ---------------------------------
    # Change number of processors
    # ---------------------------------

    npx=2; npy=2; npz=4
    HD['decomposeParDict']["numberOfSubdomains"] = npx*npy*npz
    HD['decomposeParDict']["simpleCoeffs"]["n"][0] = [npx, npy, npz]
    headerObj.header_changer(HD['decomposeParDict'])

    # ---------------------------------
    # Change environmentalProperties
    # ---------------------------------

    npx=2; npy=2; npz=2
    HD['environmentalProperties']["g"] = [1.1045, 0, 0]
    headerObj.header_changer(HD['environmentalProperties'])


