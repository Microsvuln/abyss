from abyss import abyss_filter_t
import ida_lines, ida_name, ida_hexrays as hr

VAR_ASG_VAR_SUFFIX = "_"
VAR_ASG_CALL_PREFIX = "res_"

# mapping a type string representation to a deterministic name to use
VAR_ASG_CALL_DETERMINISTIC = {
    "NTSTATUS": "status",
}

fDebug = False
def debug_print(msg):
    if fDebug:
        print("%s" % msg)
    return

def debug_lvars(lvars):
    if not fDebug:
        return
    print("%d variables" % len(lvars))
    for one in lvars:
        print("%s %s; // %s" % (one.type(), one.name, one.cmt))
    return

def set_var_unique_name(var_x, var_y, lvars):
    old_name = var_x.name
    new_name = var_y.name + VAR_ASG_VAR_SUFFIX
    new_name = set_unique_name(var_x, new_name, lvars)
    debug_print("Renamed: %s (%s) = %s " % (old_name, new_name, var_y.name))
    return

def set_func_unique_name(var_x, func_name, lvars):
    old_name = var_x.name
    x_type = var_x.type()
    if str(x_type) in VAR_ASG_CALL_DETERMINISTIC.keys():
        new_name = VAR_ASG_CALL_DETERMINISTIC[str(x_type)]
    else:
        new_name = VAR_ASG_CALL_PREFIX + func_name
    new_name = set_unique_name(var_x, new_name, lvars)
    debug_print("Renamed: %s (%s) = %s(...) " % (old_name, new_name, func_name))
    return

def set_unique_name(var_x, new_name, lvars):
    bExist = True
    while bExist:
        bExist = False
        for one in lvars:
            if new_name == one.name:
                new_name += VAR_ASG_VAR_SUFFIX
                bExist = True
                break
    var_x.name = new_name
    var_x.set_user_name()
    return new_name

class asg_visitor_t(hr.ctree_visitor_t):

    def __init__(self, cfunc):
        hr.ctree_visitor_t.__init__(self, hr.CV_FAST)
        self.cfunc = cfunc
        self.lvars = cfunc.get_lvars()
        debug_lvars(self.lvars)
        return
        
    def visit_expr(self, e):
        if e.op == hr.cot_asg:
            # is x a var?
            if e.x.op == hr.cot_var:
                # handle "x = y" types of assignments
                if e.y.op == hr.cot_var:
                    # get variable indexes
                    x_idx = e.x.v.idx
                    y_idx = e.y.v.idx
                    # get lvar_t
                    var_x = self.lvars[x_idx]
                    var_y = self.lvars[y_idx]
                    """
                    debug_print("Found: %s (user: %s, nice: %s) = %s (user: %s, nice: %s)" % (
                        var_x.name,
                        var_x.has_user_name,
                        var_x.has_nice_name,
                        var_y.name,
                        var_y.has_user_name,
                        var_y.has_nice_name))
                    """
                    # if x has an autogenerated name and y has a custom name
                    if not var_x.has_user_name and var_y.has_user_name:
                        # rename x
                        set_var_unique_name(var_x, var_y, self.lvars)
                    else:
                        debug_print("Skipped: %s = %s " % (var_x.name, var_y.name))
                # handle "x = y()" types of assignments
                elif e.y.op in [hr.cot_call, hr.cot_cast]:
                    if e.y.op == hr.cot_call:
                        tmp_y = e.y
                    elif e.y.op == hr.cot_cast and e.y.x.op == hr.cot_call:
                        tmp_y = e.y.x
                    else: # TBD
                        tmp_y = None
                    if tmp_y and tmp_y.x.op == hr.cot_obj:
                        # get name of called function
                        func_name = ida_name.get_ea_name(tmp_y.x.obj_ea,
                            ida_name.GN_VISIBLE | ida_name.GN_LOCAL)
                        # get var index and lvar_t
                        x_idx = e.x.v.idx
                        var_x = self.lvars[x_idx]
                        if not var_x.has_user_name:
                            # rename x
                            set_func_unique_name(var_x, func_name, self.lvars)
                        else:
                            debug_print("Skipped: %s = %s(...) " % (var_x.name, func_name))
        return 0


class lvars_alias_t(abyss_filter_t):
    """example filter that shows how to rename/alias local variables
    used in assigment expressions.

    examples:
    'v11 = buf' becomes 'buf_ = buf'
    'v69 = strstr(a, b)' becomes 'result_strstr = strstr(a, b)'"""

    def __init__(self):
        abyss_filter_t.__init__(self)
        return

    def process_maturity(self, cfunc, new_maturity):
        if new_maturity == hr.CMAT_FINAL:
            av = asg_visitor_t(cfunc)
            av.apply_to(cfunc.body, None)
        return 0

def FILTER_INIT():
    return lvars_alias_t()