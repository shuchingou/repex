import numpy as np
import simtk.unit as unit
from repex.thermodynamics import ThermodynamicState
from repex.replica_exchange import ReplicaExchange
from openmmtools import testsystems
from repex.utils import permute_energies
from repex import resume
import repex
import tempfile
from mdtraj.testing import eq, skipif
import nose

import logging
logging.disable(logging.INFO)  # Logging is wacky with MPI-based nose tester

test_mpi = True

try:
    from repex.mpinoseutils import mpitest    
except:
    test_mpi = False

import distutils.spawn
mpiexec = distutils.spawn.find_executable("mpiexec")

if mpiexec is None:
    test_mpi = False

def setup():
    if test_mpi == False:
        raise nose.SkipTest('No MPI detected; skipping MPI tests.')


@mpitest(2)
def test_harmonic_oscillators(mpicomm):
    nc_filename = tempfile.mkdtemp() + "/out.nc"

    T_min = 1.0 * unit.kelvin
    T_i = [T_min, T_min * 10., T_min * 100.]
    n_replicas = len(T_i)

    ho = testsystems.HarmonicOscillator()

    system = ho.system
    positions = ho.positions

    states = [ ThermodynamicState(system=system, temperature=T_i[i]) for i in range(n_replicas) ]

    coordinates = [positions] * n_replicas
    parameters = {"number_of_iterations":1000}
    replica_exchange = ReplicaExchange.create(states, coordinates, nc_filename, mpicomm=mpicomm, parameters=parameters)
    replica_exchange.run()

    u_permuted = replica_exchange.database.ncfile.variables["energies"][:]
    s = replica_exchange.database.ncfile.variables["states"][:]

    u = permute_energies(u_permuted, s)

    u0 = np.array([[ho.reduced_potential_expectation(s0, s1) for s1 in states] for s0 in states])

    l0 = np.log(u0)  # Compare on log scale because uncertainties are proportional to values
    l1 = np.log(u.mean(0))
    eq(l0, l1, decimal=1)

@mpitest(2)
def test_harmonic_oscillators_save_and_load(mpicomm):
    nc_filename = tempfile.mkdtemp() + "/out.nc"

    T_min = 1.0 * unit.kelvin
    T_i = [T_min, T_min * 10., T_min * 100.]
    n_replicas = len(T_i)

    ho = testsystems.HarmonicOscillator()

    system = ho.system
    positions = ho.positions

    states = [ ThermodynamicState(system=system, temperature=T_i[i]) for i in range(n_replicas) ]

    coordinates = [positions] * n_replicas
    parameters = {"number_of_iterations":50}
    replica_exchange = ReplicaExchange.create(states, coordinates, nc_filename, mpicomm=mpicomm, parameters=parameters)
    replica_exchange.run()
    
    replica_exchange.extend(50)

    replica_exchange = resume(nc_filename, mpicomm=mpicomm)    
    replica_exchange.run()
