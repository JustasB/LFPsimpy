import os, pytest
from ..LFPsimpy import LfpElectrode

def create_sec():
    from neuron import h

    # Create a single section
    soma = h.Section(name='soma')
    soma.insert('pas')
    soma.insert('hh')
    soma.L = soma.diam = 10

    h.pt3dadd(0, 0, 0, 10)
    h.pt3dadd(10, 0, 0, 10)


    # Inject some current
    ic = h.IClamp(0.5, sec=soma)
    ic.delay = 2

    # Generates an AP
    ic.dur = 6
    ic.amp = 1

    return soma, ic

def add_lfp_electrode():
    le = LfpElectrode(x=-100, y=50, z=0, sampling_period=0.1)

    return le

def run_sim():
    from neuron import h
    h.tstop = 10
    h.steps_per_ms = 10
    h.dt = 0.1
    h.run()

def test_no_cells():
    le = add_lfp_electrode()

    assert len(le.times) == 0
    assert len(le.values) == 0

    run_sim()

    assert len(le.times) > 0 and not any([t < 0 for t in le.times])
    assert len(le.values) > 0 and not any([v != 0 for v in le.values])


def test_one_sec_no_mpi():
    soma, ic = create_sec()
    le = add_lfp_electrode()

    assert len(le.times) == 0
    assert len(le.values) == 0

    run_sim()

    assert len(le.times) > 0 and not any([t < 0 for t in le.times])
    assert len(le.values) > 0 and any([v != 0 for v in le.values])


def test_two_electrodes():
    soma, ic = create_sec()
    le = add_lfp_electrode()

    le2 = LfpElectrode(x=100, y=50, z=0, sampling_period=0.1)

    assert len(le.times) == 0
    assert len(le.values) == 0

    assert len(le2.times) == 0
    assert len(le2.values) == 0

    run_sim()

    assert len(le.times) > 0 and not any([t < 0 for t in le.times])
    assert len(le.values) > 0 and any([v != 0 for v in le.values])

    assert len(le2.times) > 0 and not any([t < 0 for t in le2.times])
    assert len(le2.values) > 0 and any([v != 0 for v in le2.values])

    assert all([t1 == t2 for t1, t2 in zip(le.times, le2.times)])

    assert any([v1 != v2 for v1, v2 in zip(le.values, le2.values)])
    assert any([v1 == v2 for v1, v2 in zip(le.values, le2.values)])


def test_three_methods():
    soma, ic = create_sec()

    le1 = LfpElectrode(x=100, y=50, z=0, sampling_period=0.1, method='Line')
    le2 = LfpElectrode(x=100, y=50, z=0, sampling_period=0.1, method='Point')
    le3 = LfpElectrode(x=100, y=50, z=0, sampling_period=0.1, method='RC')

    run_sim()

    # from matplotlib import pyplot as plt
    # plt.plot(le1.times, le1.values)
    # plt.plot(le2.times, le2.values)
    # plt.plot(le3.times, le3.values)
    # plt.show()

    assert any([v1 != v2 for v1, v2 in zip(le1.values, le2.values)])
    assert any([v1 == v2 for v1, v2 in zip(le1.values, le2.values)])

    assert any([v1 != v3 for v1, v3 in zip(le1.values, le3.values)])
    assert any([v1 == v3 for v1, v3 in zip(le1.values, le3.values)])

def mpi_one_sec():
    from mpi4py import MPI

    from neuron import h
    pc = h.ParallelContext()
    mpirank = pc.id()
    nranks = int(pc.nhost())

    soma, ic = create_sec()
    le = add_lfp_electrode()

    assert len(le.times) == 0
    assert len(le.values) == 0

    pc.setup_transfer()
    pc.timeout(1)
    h.cvode_active(0)
    pc.set_maxstep(1)
    h.stdinit()
    pc.psolve(10)

    if mpirank == 0:
        assert len(le.times) > 0
        assert len(le.values) > 0

        from matplotlib import pyplot as plt
        plt.plot(le.times, le.values)
        plt.show()

    # Cleanup on MPI
    if nranks > 1:
        h.quit()

def test_one_sec_mpi_one_proc():
    os.system('mpiexec -np 1 python -c "from tests.test_all import mpi_one_sec as f; f()"')


def test_one_sec_mpi_two_procs():
    os.system('mpiexec -np 2 python -c "from tests.test_all import mpi_one_sec as f; f()"')


if __name__ == "__main__":
    test_three_methods()
