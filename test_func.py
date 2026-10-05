from ndot import ndot_runtime as rt

def f1(s1):
    s2 = rt.mul(s1, s1)
    return s2

s1 = 7
s2 = f1(s1)
print(s2)
