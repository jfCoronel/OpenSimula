"""Construction with an active layer (source_layer): transfer functions of a heat source
plane (radiant floor pipes), checked in steady state and against a fine finite-difference
model of the construction."""

import numpy as np
import pytest

import opensimula as osm

def floor():
    sim=osm.Simulation(); sim.console_print=False; p=sim.new_project("p")
    mats={"tile":(1.3,2300,840),"screed":(1.4,2000,1000),"insul":(0.035,30,1400),"concrete":(1.65,2300,1000)}
    for n,(k,r,c) in mats.items():
        p.new_component("Material", n).set_parameters({"conductivity":k,"density":r,"specific_heat":c})
    con=p.new_component("Construction","floor")
    con.set_parameters({"materials":["tile","screed","screed","insul","concrete"],"thicknesses":[0.01,0.03,0.03,0.03,0.20],"source_layer":2})
    p.check(); con.pre_simulation(1, 3600)
    return con, [(0.01,1.3,2300*840),(0.03,1.4,2e6),(0.03,1.4,2e6),(0.03,0.035,30*1400),(0.20,1.65,2300e3)]
def fd(layers, k_src, qs_h, T0_h, T1_h, dt=10.0, nodes_per_cm=4):
    # nodes: boundaries; T0, T1 Dirichlet at the two faces; linear inputs between hours
    xs=[0.0]; K=[]; C=[]
    for L,k,rc in layers:
        n=max(2,int(round(L*100*nodes_per_cm))); h=L/n
        for _ in range(n): K.append(k/h); C.append(rc*h); xs.append(xs[-1]+h)
    N=len(xs); cap=np.zeros(N)
    for i,c in enumerate(C): cap[i]+=c/2; cap[i+1]+=c/2
    src=sum(max(2,int(round(L*100*nodes_per_cm))) for L,_,_ in layers[:k_src])
    T=np.zeros(N); steps=int(3600/dt); hours=len(qs_h)
    A=np.zeros((N,N))
    for i,kk in enumerate(K): A[i,i]+=kk; A[i+1,i+1]+=kk; A[i,i+1]-=kk; A[i+1,i]-=kk
    M=np.diag(cap/dt)+A
    for b in (0,N-1): M[b,:]=0; M[b,b]=1
    Minv=np.linalg.inv(M)
    out=[]
    T[0]=T0_h[0]; T[-1]=T1_h[0]
    for h in range(hours-1):
        for s in range(steps):
            f=(s+1)/steps
            qs=qs_h[h]*(1-f)+qs_h[h+1]*f; t0=T0_h[h]*(1-f)+T0_h[h+1]*f; t1=T1_h[h]*(1-f)+T1_h[h+1]*f
            rhs=cap/dt*T; rhs[src]+=qs; rhs[0]=t0; rhs[-1]=t1
            T=Minv@rhs
        # fluxes out of the construction at the faces (from the node next to the face)
        q0=K[0]*(T[1]-T[0]) - cap[0]*0  # conduction towards face 0 (outward), quasi
        q1=K[-1]*(T[-2]-T[-1])
        out.append((q0,q1,T[src]))
    return np.array(out)
def ctf(con, qs, T0, T1):
    d=con._coef_Q; n=len(qs); q0=np.zeros(n); q1=np.zeros(n); tp=np.zeros(n)
    a,b,c=con._coef_T_a,con._coef_T_b,con._coef_T_c
    for t in range(n):
        def conv(coef, x):
            return sum(coef[k]*x[t-k] for k in range(len(coef)) if t-k>=0)
        def hist(y):
            return sum(d[k]*y[t-k] for k in range(1,len(d)) if t-k>=0)
        q0[t]=conv(-c,T0)+conv(b,T1)+conv(con._coef_S0,qs)-hist(q0)
        q1[t]=conv(-a,T1)+conv(b,T0)+conv(con._coef_S1,qs)-hist(q1)
        tp[t]=conv(con._coef_TP0,T0)+conv(con._coef_TP1,T1)+conv(con._coef_TPS,qs)-hist(tp)
    return q0,q1,tp

R = [0.01 / 1.3, 0.03 / 1.4, 0.03 / 1.4, 0.03 / 0.035, 0.20 / 1.65]


def test_steady_state_of_the_source():
    con, _ = floor()
    d = sum(con._coef_Q)
    R_A, R_B = sum(R[:2]), sum(R[2:])
    # the heat of the source leaves by the two sides in proportion to the other resistance
    assert sum(con._coef_S1) / d == pytest.approx(R_A / (R_A + R_B), rel=1e-6)
    assert sum(con._coef_S0) / d == pytest.approx(R_B / (R_A + R_B), rel=1e-6)
    # temperature of the plane: weighted surface temperatures and the source
    assert sum(con._coef_TP0) / d == pytest.approx(R_B / (R_A + R_B), rel=1e-6)
    assert sum(con._coef_TP1) / d == pytest.approx(R_A / (R_A + R_B), rel=1e-6)
    assert sum(con._coef_TPS) / d == pytest.approx(R_A * R_B / (R_A + R_B), rel=1e-6)


def test_dynamic_response_against_finite_differences():
    con, layers = floor()
    H = 48
    qs = np.zeros(H)
    qs[2:10] = 60.0
    T0, T1 = np.zeros(H), np.zeros(H)
    T0[20:] = 5.0
    T1[30:] = -3.0
    ref = fd(layers, 2, qs, T0, T1, dt=10.0, nodes_per_cm=4)
    q0, q1, tp = ctf(con, qs, T0, T1)
    # (in the hours the surface temperatures jump the finite differences themselves are
    # 2 % off: their error halves when the mesh is refined)
    assert np.allclose(q0[1:], ref[:, 0], rtol=0.03, atol=0.1)
    assert np.allclose(q1[1:], ref[:, 1], rtol=0.03, atol=0.02)
    assert np.allclose(tp[1:], ref[:, 2], atol=0.01)


def test_source_layer_check():
    sim = osm.Simulation()
    sim.console_print = False
    p = sim.new_project("p")
    p.new_component("Material", "m")
    c = p.new_component("Construction", "c")
    c.set_parameters({"materials": ["m", "m"], "thicknesses": [0.1, 0.1], "source_layer": 2})
    assert any("source_layer" in m.text for m in p.check() if m.level == "ERROR")
