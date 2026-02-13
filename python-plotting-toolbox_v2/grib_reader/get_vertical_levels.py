import numpy as np
import eccodes as g

def main(filename, wanted_type_of_level):

    levels = []
    names = []

    f = open(filename, 'r')
    mcount = g.codes_count_in_file(f)

    for i in range(mcount):
        gid = g.codes_any_new_from_file(f)
        typeOfLevel = g.codes_get(gid, 'typeOfLevel')
        
        if typeOfLevel == wanted_type_of_level:
            level = g.codes_get(gid, 'level')
            levels.append(level)
        g.codes_release(gid)

    f.close()

    return sorted(np.unique(levels), reverse=True)