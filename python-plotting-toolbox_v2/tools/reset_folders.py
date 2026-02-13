import os
import shutil

def refresh(path, archive=False):

    if archive == True:
        archive(path)
    if not os.path.exists(path):  # Create the outdir if it does not already exist
        os.makedirs(path)
    else:
        shutil.rmtree(path)#, onerror=readonly_handler)
        os.makedirs(path)


def archive(path):
    '''NOTE Define an archiving function here if necessary'''
    pass