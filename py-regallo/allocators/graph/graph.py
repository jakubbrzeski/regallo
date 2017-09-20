
class Node:
    def __init__(self, var):
        self.var = var

    def vid(self):
        return self.var.id

def build_graph(f):
    neighs = {var: set() for var in f.vars.values()}

    for bb in f.bblocks.values():
        live_in = list(bb.live_in)
        for (v1, v2) in zip(live_in[:-1], live_in[1:]):
            if v2 not in neighs[v1]: # and vice versa
                neighs[v2].add(v1)
                neighs[v1].add(v2)

        for instr in bb.instructions:
            defn = instr.definition
            for var in instr.live_in:
                if defn not in neighs[var]:
                    neighs[var].add(defn)
                    neighs[defn].add(var)


    return neighs


