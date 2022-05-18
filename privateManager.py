def getKey(key):
    d = dict()
    f = open('../private/key.properties', 'r')
    for line in f.readlines():
        row = line.split('=')
        row0 = row[0]
        d[row0] = row[1].strip()
    return d[key]
