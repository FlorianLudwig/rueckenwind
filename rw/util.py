import os
import shutil


if hasattr(shutil, 'which'):
    which = shutil.which
else:
    def which(cmd):
        """Return the path to an executable which would be run if the given cmd was called.

        If no cmd would be called, return None."""

        fpath, fname = os.path.split(cmd)
        if fpath:
            if is_executable(cmd):
                return cmd
        else:
            for path in os.environ['PATH'].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, cmd)
                if is_executable(exe_file):
                    return exe_file

        return None


def is_executable(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)