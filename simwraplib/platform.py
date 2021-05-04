import subprocess as sp

def get_platform():
    
    # All require different commands to find their name!        
    s = sp.Popen(['hostname'],stdout=sp.PIPE).communicate()[0]
    s += sp.Popen(['domainname'],stdout=sp.PIPE).communicate()[0]
    s += sp.Popen(['dnsdomainname'],stdout=sp.PIPE).communicate()[0]
  
    if (b'meflow' in s): 
        platform = 'local'
    elif (b'cx1' in s):
        platform = 'cx1'
    elif (b'cx2' in s): 
        platform = 'cx2'
    elif (b'eslogin' in s): 
        platform = 'archer'
    else:
        platform = 'local'

    return platform

