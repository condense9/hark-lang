# http://homepage.divms.uiowa.edu/~fleck/HaskellexprBNF.pdf

TABLE = [
    # left-assoc, non-assoc, right-assoc
    [["*", "/"], [], []],
    [["+", "-"], [], []],
    [[], ["==", "!="], []],
    [[], [], ["||", "&&"]],
]

# left assoc:  a . b . c  == (a . b) . c
# non assoc:   a . b . c  == invalid
# right assoc: a . b . c  == a . (b . c)

# right assoc eg:
# f . g . h == (f (g h))


def gen():
    res = ""

    for i, (l, n, r) in enumerate(TABLE):
        ops_l = " / ".join(f'"{o}"' for o in l) if l else "null"
        ops_n = " / ".join(f'"{o}"' for o in n) if n else "null"
        ops_r = " / ".join(f'"{o}"' for o in r) if r else "null"

        res += f"_exp{i}  = _nexp{i} / _lexp{i} / _rexp{i}\n"

        res += f"_lexp{i} = _exp{i+1} ( _op_l{i} _exp{i+1} )*\n"
        res += f"_nexp{i} = _exp{i+1} _op_n{i} _exp{i+1}\n"
        res += f"_rexp{i} = ( _exp{i+1} _op_r{i} )* _exp{i+1}\n"

        res += f"_op_l{i} = {ops_l}\n"
        res += f"_op_n{i} = {ops_n}\n"
        res += f"_op_r{i} = {ops_r}\n"

    return res


if __name__ == "__main__":
    print(gen())
