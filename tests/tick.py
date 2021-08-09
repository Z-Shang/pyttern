"""
CodeWars: Esolang: Tick
https://www.codewars.com/kata/587edac2bdf76ea23500011a
"""

from pyttern.pyttern import pyttern
from fpy.composable.collections import transN, apply
from fpy.data.either import Left, Right, isRight, fromLeft

inc = lambda x: (x + 1) % 256
end = lambda x: len(x) - 1

@pyttern
def interp(f, r, t, p, o): {
    ('<', _r, _t, 0, _o)        : Right((_r[0], _r[1:], [0] + _t, 0, _o)),
    ('<', _r, _t, _p, _o)       : Right((_r[0], _r[1:], _t, _p - 1, _o)),
    ('>', _r, _t, end(t), _o)   : Right((_r[0], _r[1:], _t + [0], p + 1, _o)),
    ('>', _r, _t, _p, _o)       : Right((_r[0], _r[1:], _t, _p + 1, _o)),
    ('+', _r, _t, _p, _o)       : Right((_r[0], _r[1:], transN(_p, inc, _t), _p, _o)),
    ('*', _r, _t, _p, _o)       : Right((_r[0], _r[1:], _t, _p, _o + chr(_t[_p]))),
    ('*', (), _t, _p, _o)       : Left(_o + chr(_t[_p])),
    (_f, (), _t, _p, _o)        : Left(_o),
    _                           : Left(None)
}

def tick(inp):
    if not inp:
        return ''
    nxt = interp(inp[0], inp[1:], [0], 0, '')
    # well, it is a shame to not do a recursion because of Python's call stack depth limitation
    while isRight(nxt):
        nxt = nxt >> apply(interp)
    return fromLeft("", nxt)

if __name__ == '__main__':
    # Hello World Taken from CodeWars
    test = '++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*>+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*>++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++**>+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*>++++++++++++++++++++++++++++++++*>+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*<<*>>>++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*<<<<*>>>>>++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++*>+++++++++++++++++++++++++++++++++*'
    print(tick(tuple(test)))
