import cfg
import utils

# Assumption there is only one store for a given memslot.
def data_flow_is_correct(f, f_orig):
    # Mapping of variable id to the instruction this variable is defined in
    # and memslots to the corresponding store instruction. We store the map
    # for the new function and the original one.
    defs_new = {} 
    defs_orig = {}
   
    for bb in f.bblocks.values():
        for instr in bb.instructions:
            # We skip instructions inserted in phi elimination phase.
            if instr.ssa:
                if instr.definition: 
                    defs_new[instr.definition.id] = instr
                elif instr.opname == cfg.Instruction.STORE:
                    # In the store operation defined by the framework
                    # memslot is always the first argument.
                    memslot = instr.uses_debug[0]
                    defs_new[memslot] = instr

    for bb in f_orig.bblocks.values():
        for instr in bb.instructions:
            if instr.definition:
                defs_orig[instr.definition.id] = instr

    # This function takes a variable var and follows
    # its data flow path up (through movs, load and stores)
    # until it reaches its definition. If this definition
    # corresponds to var_orig definition, returns True.
    # Otherwise, or if it can't find definition, returns False.
    def find_original_definition(var, var_orig):
        no_def = (var_orig.id not in defs_orig)
        tmp = var
        while True:
            if tmp.id not in defs_new:
                if no_def:
                    # Original variable had no definition
                    # (e.g. it could be a function argument).
                    break 
                else:
                    return False

            pred = defs_new[tmp.id]
            if pred.original:
                if pred.original.definition == var_orig:
                    # Correct. We found the definition and it corresponds 
                    # to the original definition.
                    break
                else:
                    return False

            # If the instruction is not a copy of the original but was
            # inserted during register allocation, it may be a load or mov.
            # Store instructions inserted by register allocator shouldn't
            # define new variables.
            if pred.opname == cfg.Instruction.MOV:
                # A mov instruction should have one Variable use.
                if not (len(pred.uses_debug) == 1 and isinstance(pred.uses_debug[0], cfg.Variable)):
                    return False
                tmp = pred.uses_debug[0]

            elif pred.opname == cfg.Instruction.LOAD:
                # A load instruction should have one memslot use.
                if not(len(pred.uses_debug) == 1 and utils.is_slotname(pred.uses_debug[0])):
                    return False
                # Find a memslot definition (i.e. corresponding store instruction).
                memslot = pred.uses_debug[0]
                if memslot not in defs_new:
                    if no_def:
                        # Original variable had no definition
                        # so there should be no store.
                        break
                    else:
                        return False
                
                store = defs_new[memslot]
                # A store instruction should have two input arguments: memslot and Variable (in this order).
                if not(len(store.uses_debug) == 2 and isinstance(store.uses_debug[1], cfg.Variable)):
                    return False

                tmp = store.uses_debug[1]

        return True

    # MAIN LOOP
    for bb in f.bblocks.values():
        for instr in bb.instructions:
            # For all instructions that are copies of the original ones.
            if instr.original is not None:
                for var in instr.uses:
                    index = instr.uses_debug.index(var)
                    var_orig = instr.original.uses_debug[index]
                   
                    # Skip variables defined in phi instruction.
                    if var_orig.id in defs_orig and defs_orig[var_orig.id].is_phi():
                        continue

                    success = find_original_definition(var, var_orig)
                    if not success:
                        return False
   
    return True
                            

# Checks whether at every program point every live variable has a register assigned
# and any two live variables have different register assigned. In other words, mapping
# from live variables to registers is injection.
def allocation_is_correct(f):
    f.perform_liveness_analysis()

    def allocation_is_injection(varset):
        regs = set()
        for var in varset:
            if not utils.is_regname(var.alloc) or var.alloc in regs:
                return False
            regs.add(var.alloc)
        return True
    
    for bb in f.bblocks.values():
        if not allocation_is_injection(bb.live_in):
            return False
        for instr in bb.instructions:
            if not allocation_is_injection(instr.live_out):
                return False

    return True

