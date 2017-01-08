def read_cfg():

    cfg = {}
    with open('creds.cfg') as hlr:
        for line in hlr:
            split_line = line.split('::')
            cfg[split_line[0].strip()] = split_line[1].strip()
    return cfg
