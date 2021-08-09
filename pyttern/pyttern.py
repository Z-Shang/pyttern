import bytecode as bc

from pyttern.core import _fresh, _v, pytternd, NonExhaustivePatternError

from fpy.composable.collections import is_, and_, or_
from fpy.data.maybe import Just, Nothing, isJust, fromJust
from fpy.experimental.do import do
from fpy.parsec.parsec import one, many, neg, skip
from fpy.utils.placeholder import __

isInstr = is_(bc.Instr)
popTop = and_(isInstr, __.name == "POP_TOP")
none = and_(isInstr, and_(__.name == "LOAD_CONST", __.arg == None))
ret = and_(isInstr, __.name == "RETURN_VALUE")
ending = one(popTop) >> one(none)>> one(ret)
mkConstMap = and_(isInstr, __.name == "BUILD_CONST_KEY_MAP")
mkMap = and_(isInstr, __.name == "BUILD_MAP")
isArg = and_(isInstr, __.name == "LOAD_FAST")
isLoadGlobal = and_(isInstr, __.name == "LOAD_GLOBAL")
isWildcard = and_(isLoadGlobal, __.arg == "_")
isVarName = lambda x: x != "_" and x.startswith("_")
isVar = and_(isLoadGlobal, __.arg ^ isVarName)

varMapEnding = one(mkMap) << ending
constMapEnding = one(mkConstMap) << ending


def exprToLambda(b, place, filename, args, fv, v=None):
    varMap = {arg : _fresh(arg) for arg in args}
    mod_b = []
    for instr in b:
        if isArg(instr):
            name = instr.arg
            instr.arg = varMap[name]
        if isVar(instr):
            name = instr.arg
            assert name in v, f"Variable: {name} is not bound"
            instr = bc.Instr("LOAD_FAST", varMap[v[name]])
        mod_b.append(instr)
    mod_b.append(bc.Instr("RETURN_VALUE"))
    lm = bc.Bytecode(mod_b)
    lm.freevars.extend(fv)
    lm.argcount = len(varMap)
    lm.argnames.extend(list(varMap.values()))
    lm.name = _fresh(place, "exprlambda")
    lm.filename = filename
    lm.flags = lm.flags | 16
    lm.update_flags()
    co = lm.to_code()
    return [bc.Instr("LOAD_CONST", co), bc.Instr("LOAD_CONST", lm.name), bc.Instr("MAKE_FUNCTION", 0)]

def generateDefault(place, filename, args):
    varMap = {arg : _fresh(arg) for arg in args}
    lm = bc.Bytecode([bc.Instr("LOAD_CONST", NonExhaustivePatternError)])
    lm.append(bc.Instr("LOAD_CONST", f"Non Exhaustive Pattern Matching: {place}"))
    for k, v in varMap.items():
        lm.append(bc.Instr("LOAD_CONST", f"\n{k}: "))
        lm.append(bc.Instr("LOAD_FAST", v))
        lm.append(bc.Instr("FORMAT_VALUE", 0x02))
    lm.append(bc.Instr("BUILD_STRING", 1 + 2 * len(varMap)))
    lm.append(bc.Instr("CALL_FUNCTION", 1))
    lm.append(bc.Instr("RAISE_VARARGS", 1))
    lm.argcount = len(varMap)
    lm.argnames.extend(list(varMap.values()))
    lm.name = _fresh(place, "defaultcase")
    lm.filename = filename
    lm.flags = lm.flags | 16
    lm.update_flags()
    co = lm.to_code()
    return [bc.Instr("LOAD_CONST", co), bc.Instr("LOAD_CONST", lm.name), bc.Instr("MAKE_FUNCTION", 0)]


def partitionInst(insts, n):
    if not insts:
        return [], []
    if n == 0:
        return [], insts
    head = insts[-1]
    # print(f"{head = }")
    # print(f"{n = }")
    pre, post = head.pre_and_post_stack_effect()
    # print(f"{pre = }")
    # print(f"{post= }")
    if pre > 0:
        if pre == n:
            return [head], insts[:-1]
        if pre < n:
            nxt, rst = partitionInst(insts[:-1], n - pre)
            return nxt + [head], rst
    if pre == 0:
        nxt, rst = partitionInst(insts[:-1], n - post)
        return nxt + [head], rst
    pre = abs(pre)
    nxt, rst = partitionInst(insts[:-1], pre)
    if post == n:
        return nxt + [head], rst
    if post < n:
        head = nxt + [head]
        nxt, rst = partitionInst(rst, n - post)
        return nxt + head, rst


def transConstMap(b, mk, fn_name, filename, args, fv):
    body = b[:-4]
    keynames = body[-1]
    exprs = []
    rest = body[:-1]
    while rest:
        expr, rest = partitionInst(rest, 1)
        exprs.append(expr)
    lms = [exprToLambda(e, fn_name, filename, args, fv) for e in reversed(exprs)]
    resbc = bc.Bytecode(sum(lms, start=[]))
    resbc.append(keynames)
    resbc.append(mk)
    resbc.append(bc.Instr("LOAD_METHOD", "get"))
    for arg in args:
        resbc.append(bc.Instr("LOAD_FAST", arg))
    resbc.append(bc.Instr("BUILD_TUPLE", arg=len(args)))
    resbc.extend(generateDefault(fn_name, filename, args))
    resbc.append(bc.Instr("CALL_METHOD", 2))
    for arg in args:
        resbc.append(bc.Instr("LOAD_FAST", arg))
    resbc.append(bc.Instr("CALL_FUNCTION", arg=len(args)))
    resbc.append(bc.Instr("RETURN_VALUE"))
    return resbc


def transVarMap(b, mk, fn_name, filename, args, fv):
    body = b[:-4]
    parts = []
    rest = body
    hasDefault = False
    defaultExpr = []
    while rest:
        part, rest = partitionInst(rest, 2)
        expr, pat = partitionInst(part, 1)
        if isWildcard(pat[0]) and len(pat) == 1:
            assert not hasDefault, f"Duplicated default cases in {fn_name}, line {pat[0].lineno} @ {filename}"
            hasDefault = True
            defaultExpr = exprToLambda(expr, fn_name, filename, args, fv)
        else:
            vbind = {}
            vpat = []
            mkTpl = pat[-1]
            raw_pat_parts = pat[:-1]
            pat_parts = []
            while raw_pat_parts:
                pat_part, raw_pat_parts = partitionInst(raw_pat_parts, 1)
                pat_parts.append(pat_part)
            for i, v in enumerate(reversed(pat_parts)):
                if len(v) == 1 and isVar(v[0]):
                    vbind[v[0].arg] = args[i]
                    vpat.append(bc.Instr("LOAD_CONST", _v(v[0].arg)))
                else:
                    vpat.extend(v)
            vpat.append(mkTpl)
            parts.append((vpat, exprToLambda(expr, fn_name, filename, args, fv, vbind)))
    if not hasDefault:
        defaultExpr = generateDefault(fn_name, filename, args)
    defaultPat = []
    for _ in args:
        defaultPat.append(bc.Instr("LOAD_CONST", _v()))
    defaultPat.append(bc.Instr("BUILD_TUPLE", len(args)))
    resbc = bc.Bytecode([bc.Instr("LOAD_CONST", pytternd)])
    for pat, expr in reversed(parts):
        resbc.extend(pat)
        resbc.extend(expr)
    resbc.extend(defaultPat)
    resbc.extend(defaultExpr)
    if not hasDefault:
        mk.arg += 1
    resbc.append(mk)
    resbc.append(bc.Instr("CALL_FUNCTION", 1))
    for arg in args:
        resbc.append(bc.Instr("LOAD_FAST", arg))
    resbc.append(bc.Instr("BUILD_TUPLE", arg=len(args)))
    resbc.append(bc.Instr("BINARY_SUBSCR"))
    for arg in args:
        resbc.append(bc.Instr("LOAD_FAST", arg))
    resbc.append(bc.Instr("CALL_FUNCTION", arg=len(args)))
    resbc.append(bc.Instr("RETURN_VALUE"))
    return resbc

@do(Just)
def _deco(rawbc, fn_name, filename, args, fv):
    mapType = many(skip(neg(or_(mkConstMap, mkMap))) | skip(one(or_(mkConstMap, mkMap)) >> neg(popTop)) | (varMapEnding | constMapEnding)) 
    mapEnding, rest <- mapType(rawbc)
    if rest:
        Nothing()
    else:
        return {
            'BUILD_MAP' : transVarMap,
            'BUILD_CONST_KEY_MAP' : transConstMap
        }[mapEnding[0].name](rawbc, mapEnding[0], fn_name, filename, args, fv)

def isVarargFn(fn):
    return 1 == ((fn.__code__.co_flags >> 2) & 1)

# Not using the name `match` as it may conflict with the Python one
def pyttern(fn):
    rawbc = bc.Bytecode.from_code(fn.__code__)
    argcount = fn.__code__.co_argcount + (1 if isVarargFn(fn) else 0)
    args = fn.__code__.co_varnames[: argcount]

    # print( f"Generating pattern matching for function: {fn.__name__} at line: {rawbc.first_lineno} @ {rawbc.filename}")
    resbc = _deco(rawbc, fn.__name__, rawbc.filename, args, rawbc.freevars)
    assert isJust(resbc), f"Failed to generate pattern matching for function: {fn.__name__} at line: {rawbc.first_lineno} @ {rawbc.filename}"
    res = fromJust(resbc)
    res.freevars.extend(rawbc.freevars)
    res.cellvars.extend(rawbc.cellvars)
    res.argcount = rawbc.argcount
    res.argnames.extend(rawbc.argnames)
    res.name = rawbc.name
    res.filename = rawbc.filename
    res.flags = rawbc.flags
    res.update_flags()
    fn.__code__ = res.to_code()
    return fn


if __name__ == "__main__":
    # @pyttern
    # def g(a, *b): {
        # (1, (2,)) : f"{a}, {b}",
        # (3, (4, 5)) : b,
    # }

    # print(g(1, 2))
    # print(g(3, 4, 5))
    # print(g(5, 6))

    # @pyttern
    # def f(): {
    # }

    @pyttern
    def h(a, b): {
        (2, _2) : _2 * 2,
            _ : 100
    }

    print(h(1, 2))
    print(h(2, 10))

