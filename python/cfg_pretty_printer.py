import cfg

class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    ENDC = '\033[0m'


def print_variable(var, **kwargs):
    print_llvm_ids = kwargs.get("llvm_ids", False)
    if not var.local:
        res = "@" + var.id
    else:
        res = var.id
    if print_llvm_ids and len(var.llvm_id) > 0:
        res = res + "(" + var.llvm_id + ")"
    return res


def print_instruction(instr, **kwargs):
    live_vars = kwargs.get("live_vars", [])
    res = Colors.YELLOW + print_variable(instr.definition, **kwargs) + " = " 
    res = res + Colors.RED + instr.opname + Colors.YELLOW
    if instr.is_phi():
        for use in instr.phi_uses:
            bb_id, v = use
            res = res + " (" + bb_id + " -> " + print_variable(v, **kwargs) + "),"
    else:
        for use in instr.uses:
            res = res + " " + print_variable(use, **kwargs) + ","
        
    res = res + Colors.ENDC

    if len(live_vars) > 0:
        res = res + "  | " + Colors.GREEN
        assert instr.live_in is not None
        live_ids = [v.id for v in list(instr.live_in)]
        for i in range(len(live_vars)):
            if live_vars[i] in live_ids:
                res = res + " (" + str(live_vars[i]) + ")"
        
    return res + Colors.ENDC


def print_basic_block(bb, **kwargs):
    print_llvm_ids = kwargs.get("llvm_ids", False)
    print_uev_def = kwargs.get("uev_def", True)
    print_liveness = kwargs.get("liveness", False)
    print_dominance = kwargs.get("dominance", False)

    # result string
    res = bb.id 
    if bb.llvm_id is not None:
        res = res + "(" + bb.llvm_id + ")"

    for instr in bb.instructions:
        res = res + "\n  > " + print_instruction(instr, **kwargs)
    
    # successors
    res = res + "\n  SUCC: ["
    succs_ids = bb.succs.keys()
    for i in range(len(succs_ids)):
        if i:
            res = res + ", "
        res = res + succs_ids[i]
    res = res + "]"

    # dominators
    if print_dominance:
        assert bb.dominators is not None
        dominators = list(bb.dominators)
        res = res + "\n  DOM: ["
        for i in range(len(dominators)):
            if i:
                res = res + ", "
            res = res + dominators[i].id
        res = res + "]"

    # upword-exposed vars and definitions
    if print_uev_def:
        assert bb.uevs is not None
        # uevars
        res = res + "\n  UEV: "
        iter_uevs = [(k,v) for (k,v) in bb.uevs.iteritems()]
        for i in range(len(iter_uevs)):
            if i:
                res = res + "\n       "
            (bid, uevset) = iter_uevs[i]
            res = res + "(" + bid + " -> "
            uevlist = list(uevset)
            res = res + "["
            for i in range(len(uevlist)):
                if i:
                    res = res + ", "
                res = res + print_variable(uevlist[i], **kwargs)
            res = res + "]"    
            res = res + ")"
        
        # definitions
        assert bb.defs is not None
        defs = list(bb.defs)
        res = res + "\n  DEFS: ["
        for i in range(len(defs)):
            if i:
                res = res + ", "
            res = res + print_variable(defs[i], **kwargs)
        res = res + "]"

    # live variables
    if print_liveness:
        assert bb.live_in is not None and bb.live_out is not None
        # live-in 
        live_in_list = list(bb.live_in)
        res = res + "\n  LIVE-IN: ["
        for i in range(len(live_in_list)):
            if i:
                res = res + ", "
            res = res + print_variable(live_in_list[i], **kwargs)
        res = res + "]"
        # live-out
        live_out_list = list(bb.live_out)
        res = res + "\n  LIVE-OUT: ["
        for i in range(len(live_out_list)):
            if i:
                res = res + ", "
            res = res + print_variable(live_out_list[i], **kwargs)
        res = res + "]"

    return res


def print_function(f, **kwargs):
    print_bb_live_sets = kwargs.get("bb_live_sets", True)
    print_uev_def = kwargs.get("uev_def", True)

    res = "FUNCTION " + f.name
    for bb in f.bblocks.values():
        res = res + "\n" + print_basic_block(bb, **kwargs)
                   
    return res



