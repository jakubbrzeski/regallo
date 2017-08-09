class BasicCost:
    def cost(instr):
        ld = math.pow(10, instr.get_loop_depth())
        if instr.opname == cfg.Instruction.LOAD:
            return 2*ld
        elif instr.opname == cfg.Instruction.STORE:
            return 2*ld
        else:
            return ld

    def cost_of_list(instr_list):
        res = 0
        for instr in instr_list:
            res += cost(instr)

        return res

    def cost_of_bb(bb):
        return cost_of_list(bb.instructions)

    def cost_of_function(f):
        res = 0
        for bb in f.bblocks.values():
            res += cost_of_bb(bb)

        return res



