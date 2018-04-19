filedict = {}
with open("./input/inputfile") as f:
    filestr = f.read().split("\n")
    a = filestr[1]
    b = filestr[3]
    print("Hello World " + a + " " + b + "\n")

