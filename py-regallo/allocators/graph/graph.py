class Node:
    def __init__(self, var):
        self.var = var

    def vid(self):
        return self.var.id

def build_interference_graph(f):
    neighs = {var: set() for var in f.vars.values()}

    for bb in f.bblocks.values():
        live_in = list(bb.live_in)
        # Add clique from all variables live-in at the basic block.
        for v1 in bb.live_in:
            for v2 in bb.live_in:
                if v2 not in neighs[v1] and v2 != v1:
                    neighs[v2].add(v1)
                    neighs[v1].add(v2)
       
        # For each live-out definition add edges with all other live-out variables.
        for instr in bb.instructions:
            defn = instr.definition
            if defn in instr.live_out:
                for var in instr.live_out:
                    if defn not in neighs[var]:
                        if var != defn:
                            neighs[var].add(defn)
                            neighs[defn].add(var)


    return neighs


