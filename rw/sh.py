import subprocess as sp
from shutil import *


def source(path):
    """execute givin path in bash and return environment as dict

    This simulates "source /path" where /path is a shell scripts"""
    proc = sp.Popen(['bash', '-c', 'source ' + path + ' && env'], stdout=sp.PIPE)
    stdoutdata, stderrdata = proc.communicate()
    if stderrdata:
        raise AttributeError(stderrdata)
    ret = {}
    for line in stdoutdata.split('\n'):
        key, _, value = line.partition('=')
        ret[key] = value
    return ret
