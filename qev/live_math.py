"""Exact Q(zeta_8) operators. zeta_8**4 = -1; q0 is the low bit."""
from fractions import Fraction as F
from .live_common import Rejected, need, fields


class Unsupported(ValueError):
    pass


class E:
    def __init__(self, value=0):
        self.c = tuple(F(x) for x in value) if isinstance(value, (tuple, list)) else (F(value), F(0), F(0), F(0))

    def __add__(self, other):
        other = other if isinstance(other, E) else E(other)
        return E(tuple(a+b for a, b in zip(self.c, other.c)))

    __radd__ = __add__

    def __neg__(self):
        return E(tuple(-x for x in self.c))

    def __sub__(self, other):
        return self + -as_e(other)

    def __rsub__(self, other):
        return as_e(other) + -self

    def __mul__(self, other):
        other = as_e(other)
        c = [F(0)] * 4
        for i, a in enumerate(self.c):
            for j, b in enumerate(other.c):
                c[(i+j) % 4] += a*b * (1 if i+j < 4 else -1)
        return E(c)

    __rmul__ = __mul__

    def inverse(self):
        need(self != E(), 'ZERO_DIVISION')
        cols = [(self * E(tuple(int(i == j) for i in range(4)))).c for j in range(4)]
        a = [[cols[j][i] for j in range(4)] + [F(int(i == 0))] for i in range(4)]
        for j in range(4):
            k = next(i for i in range(j, 4) if a[i][j])
            a[j], a[k] = a[k], a[j]
            d = a[j][j]
            a[j] = [v/d for v in a[j]]
            for i in range(4):
                if i != j:
                    d = a[i][j]
                    a[i] = [v-d*w for v, w in zip(a[i], a[j])]
        return E(tuple(a[i][4] for i in range(4)))

    def __truediv__(self, other):
        return self * as_e(other).inverse()

    def __eq__(self, other):
        return self.c == as_e(other).c

    def wire(self):
        return [str(x) for x in self.c]


def as_e(x):
    return x if isinstance(x, E) else E(x)


Z = E((0, 1, 0, 0))
I = Z*Z
S = (Z-Z*Z*Z)/2
ANGLE_K = {'0.0': 0, '1.5707963267948966': 1, '-1.5707963267948966': -1,
           '3.141592653589793': 2, '-3.141592653589793': -2,
           '4.71238898038469': 3, '6.283185307179586': 4}
PHASE_K = {'0.0': 0, '2.3561944901923475': 3, '1.5707963267948966': 2,
           '3.141592653589793': 4}


def zp(k):
    value = E(1)
    for _ in range(k % 8):
        value = value*Z
    return value


def project(snapshot):
    fields(snapshot, ('cregs', 'global_phase', 'name', 'num_clbits', 'num_qubits', 'operations'))
    width = snapshot['num_qubits']
    need(type(width) is int and 2 <= width <= 156, 'QUBIT_WIDTH')
    need(type(snapshot['num_clbits']) is int and snapshot['num_clbits'] == 2, 'CLBIT_WIDTH')
    need(snapshot['cregs'] == [{'name': 'meas', 'size': 2}]
         and type(snapshot['cregs'][0]['size']) is int, 'REGISTER')
    need(type(snapshot['operations']) is list and 1 <= len(snapshot['operations']) <= 128, 'OPERATIONS')
    need(type(snapshot['global_phase']) is str, 'GLOBAL_PHASE_TYPE')
    if snapshot['global_phase'] not in PHASE_K:
        raise Unsupported('GLOBAL_PHASE_LITERAL')
    matrix = [[E(int(r == c))*zp(PHASE_K[snapshot['global_phase']]) for c in range(4)] for r in range(4)]
    measured = {}
    tokens = [snapshot['global_phase']]
    for op in snapshot['operations']:
        fields(op, ('clbits', 'name', 'params', 'qubits'))
        name, qs, cs, params = (op[k] for k in ('name', 'qubits', 'clbits', 'params'))
        need(type(name) is str and type(qs) is list and type(cs) is list and type(params) is list, 'OP_TYPES')
        need(all(type(q) is int and 0 <= q < width for q in qs) and len(qs) == len(set(qs)), 'QUBIT_DOMAIN')
        need(all(type(c) is int and 0 <= c < 2 for c in cs) and len(cs) == len(set(cs)), 'CLBIT_DOMAIN')
        # Idle wires are removed only after every operation's wires are checked.
        need(set(qs) <= {0, 1}, 'UNMAPPED_ACTIVE_WIRE')
        need(name not in ('if_else', 'while_loop', 'for_loop', 'switch_case', 'reset',
                          'reset_2', 'measure_2', 'measure_reset', 'measure_reset_2'),
             'FORBIDDEN_DYNAMIC_OR_RESET_GATE')
        if name not in ('h', 'x', 'cx', 'cz', 'sx', 'rz', 'barrier', 'measure'):
            raise Unsupported('GATE_' + name)
        if name == 'measure':
            need(len(qs) == len(cs) == 1 and not params, 'MEASURE_ARITY')
            need(qs[0] not in measured and cs[0] not in measured.values(), 'REPEATED_MEASUREMENT')
            measured[qs[0]] = cs[0]
            continue
        need(not measured, 'MID_CIRCUIT_MEASUREMENT')
        need(not cs, 'GATE_CLBITS')
        if name == 'barrier':
            need(bool(qs) and not params, 'BARRIER_ARITY')
            continue
        need(len(qs) == (2 if name in ('cx', 'cz') else 1), 'GATE_ARITY')
        need(len(params) == (1 if name == 'rz' else 0) and all(type(p) is str for p in params), 'GATE_PARAMS')
        if name == 'rz':
            if params[0] not in ANGLE_K:
                raise Unsupported('RZ_LITERAL')
            k = ANGLE_K[params[0]]
            gate = [[zp(-k), E()], [E(), zp(k)]]
            tokens.extend(params)
        elif name == 'h':
            gate = [[S, S], [S, -S]]
        elif name == 'x':
            gate = [[E(), E(1)], [E(1), E()]]
        elif name == 'sx':
            gate = [[(1+I)/2, (1-I)/2], [(1-I)/2, (1+I)/2]]
        out = [[E() for _ in range(4)] for _ in range(4)]
        for r in range(4):
            for c in range(4):
                if name == 'cx':
                    target = r ^ (1 << qs[1]) if r & (1 << qs[0]) else r
                    out[target][c] = out[target][c] + matrix[r][c]
                elif name == 'cz':
                    out[r][c] = matrix[r][c] * (-1 if all(r & (1 << q) for q in qs) else 1)
                else:
                    bit = (r >> qs[0]) & 1
                    for b in range(2):
                        target = (r & ~(1 << qs[0])) | (b << qs[0])
                        out[target][c] = out[target][c] + gate[b][bit]*matrix[r][c]
        matrix = out
    need(set(measured) == {0, 1} and set(measured.values()) == {0, 1}, 'MISSING_MEASUREMENT')
    pivot = next(x for row in matrix for x in row if x != 0)
    # All allowed gates are unitary. Dividing the first nonzero entry gives a
    # unique projective representative; no individual column phases discarded.
    normalized = [[(x/pivot).wire() for x in row] for row in matrix]
    return {'operator': normalized,
            'measurement': [[str(q), str(measured[q])] for q in (0, 1)],
            'basis': 'q1q0:00,01,10,11', 'angleMap': 'qev-ideal-angle-literals-v1',
            'globalPhasePolicy': 'QUOTIENT_SINGLE_GLOBAL_PHASE',
            'tokens': tokens, 'originalWidth': str(width)}


def main():
    import sys
    from .live_common import parse, encode
    try:
        result = {'state': 'evaluated', 'value': project(parse(sys.stdin.buffer.read(4_194_305)))}
    except Unsupported as exc:
        result = {'state': 'unresolved', 'reason': 'UNSUPPORTED:' + str(exc)}
    except Rejected as exc:
        result = {'state': 'unresolved', 'reason': 'REJECTED:' + str(exc)}
    sys.stdout.buffer.write(encode(result))


if __name__ == '__main__':
    main()
