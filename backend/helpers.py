from os.path import abspath, dirname, join
this_dir = dirname(abspath(__file__))
def load_keys():
    keyfile = join(this_dir, 'keys.txt')
    keydict = dict()
    with open(keyfile, 'r') as fr:
        for line in fr:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue
            username, key = line.split()
            keydict[key] = username
    return keydict
