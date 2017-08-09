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
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def var_str(var, **kwargs):
    print_llvm_names = kwargs.get("llvm_names", False)
    res = var.id
    if print_llvm_names and len(var.llvm_name) > 0:
        res = res + "(" + var.llvm_name + ")"
    return res

def value_str(val, **kwargs):
    # if val is variable then var_str
    # if not, print the value as a string
    if isinstance(val, cfg.Variable):
        return Colors.YELLOW + Colors.BOLD + var_str(val) + Colors.ENDC
    else:
        return str(val)


def sorted_varlist_str(var_list, **kwargs):
    res = "["
    # variable ids are of the form "v[0-9]+" so we sort it by the numerical suffix
    sorted_var_list = sorted(var_list, key=lambda v: int(v.id[1:]))
    for i in range(len(sorted_var_list)):
        if i:
            res = res + ", "
        res = res + var_str(sorted_var_list[i], **kwargs)
    return res + "]"

def id_list_str(id_list, **kwargs):
    res = "["
    for i in range(len(id_list)):
        if i:
            res = res + ", "
        res = res + id_list[i]
    return res + "]"

def instruction_str(instr, **kwargs):
    live_vars = kwargs.get("live_vars", [])
    loop_depth = kwargs.get("loop_depth", False)
    nums = kwargs.get("instr_nums", None)
    intervals = kwargs.get("intervals", None)
    print_interval_for = kwargs.get("print_interval_for", None)

    res = ""

    if print_interval_for:
        assert intervals is not None and nums is not None
        num = nums.get(instr.id)
        ivs = intervals[print_interval_for]
        for iv in ivs:
            if iv.fr <= num and num <= iv.to:
                res = res + Colors.GREEN + " | " + Colors.ENDC
    
    if nums is not None:
        res = res + " " + str(nums.get(instr.id)) + ": "
    else:
        res = res + " > "

    res = res + value_str(instr.definition, **kwargs) + " = " 
    res = res + Colors.RED + instr.opname + Colors.ENDC

    if instr.is_phi():
        for (bb_id, v) in zip(instr.phi_preds, instr.uses_debug):
            res = res + " (" + value_str(bb_id, **kwargs) + " -> " + value_str(v, **kwargs) + ")"
    else:
        for use in instr.uses_debug:
            res = res + " " + value_str(use, **kwargs)
    
    if loop_depth:
        res = res + "  | " + Colors.GREEN + "loop depth: " + str(instr.get_loop_depth())
    if len(live_vars) > 0:
        res = res + "  | " + Colors.GREEN
        assert instr.live_in is not None
        live_ids = [v.id for v in list(instr.live_in)]
        for i in range(len(live_vars)):
            if live_vars[i] in live_ids:
                res = res + " (" + str(live_vars[i]) + ")"
        
    return res + Colors.ENDC


def basic_block_str(bb, **kwargs):
    print_llvm_names = kwargs.get("llvm_names", False)
    print_succ = kwargs.get("succ", False)
    print_uev_def = kwargs.get("uev_def", False)
    print_liveness = kwargs.get("liveness", False)
    print_dominance = kwargs.get("dominance", False)

    # result string
    res = Colors.UNDERLINE + bb.id 
    if bb.llvm_name is not None:
        res = res + " (" + bb.llvm_name + ")"
    res = res + Colors.ENDC

    for instr in bb.instructions:
        res = res + "\n  " + instruction_str(instr, **kwargs)

    res = res + "\n"

    # successors (ids are of the form "bb[0-9]+" so we sort it by the numerical suffix)
    if print_succ:
        res = res + "\n  SUCC: " + id_list_str(
                sorted(bb.succs.keys(), key=lambda bid: int(bid[2:])), **kwargs)

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
        res = res + "\n  UEV: {"
        iter_uevs = [(k,v) for (k,v) in bb.uevs.iteritems()]
        for i in range(len(iter_uevs)):
            if i:
                res = res + "\n        "
            (bid, uevset) = iter_uevs[i]
            res = res + bid + " -> " + sorted_varlist_str(list(uevset), **kwargs)
        res = res + "}" 
        
        # definitions
        assert bb.defs is not None
        res = res + "\n  DEFS: " + sorted_varlist_str(list(bb.defs), **kwargs)

    # live variables
    if print_liveness:
        assert bb.live_in is not None and bb.live_out is not None
        # live-in
        res = res + "\n  LIVE-IN: " + sorted_varlist_str(list(bb.live_in), **kwargs)
        # live-out
        res = res + "\n  LIVE-OUT: " + sorted_varlist_str(list(bb.live_out), **kwargs)

    return res


def function_str(f, **kwargs):
    print_bb_live_sets = kwargs.get("bb_live_sets", True)
    print_uev_def = kwargs.get("uev_def", True)

    res = "FUNCTION " + f.name
    sorted_bblocks = sorted(f.bblocks.values(), key=lambda bb: bb.id)
    for bb in sorted_bblocks:
        res = res + "\n" + basic_block_str(bb, **kwargs) + "\n"
                   
    return res


def intervals_str(intervals, **kwargs):
    all_ivs = []
    for ivlist in intervals.values():
        all_ivs.extend(ivlist)

    all_ivs = sorted(all_ivs, key=lambda iv: (iv.fr, iv.to))

    res = ""
    for iv in all_ivs:
        res += "[" + str(iv.fr) + ", " + str(iv.to) + "] " + value_str(iv.var) + "\n"

    return res
