import numpy as np
import simtk.unit as unit
from repex.thermodynamics import ThermodynamicState
from repex import hamiltonian_exchange
from repex import testsystems
from repex.utils import permute_energies
import tempfile
from mdtraj.testing import eq
from repex.constants import kB


def test_power_oscillators():
    """Test HREX with power oscillators reduced potentials."""

    nc_filename = tempfile.mkdtemp() + "/out.nc"

    temperature = 1 * unit.kelvin

    K0 = 100.0  # Units are automatically added by the testsystem
    K = [K0, K0 * 10., K0 * 1.]
    powers = [2., 2., 4.]
    n_replicas = len(K)

    oscillators = [testsystems.PowerOscillator(b=powers[i]) for i in range(n_replicas)]

    systems = [ho.system for ho in oscillators]
    positions = [ho.positions for ho in oscillators]

    state = ThermodynamicState(system=systems[0], temperature=temperature)

    replica_exchange = hamiltonian_exchange.HamiltonianExchange.create_repex(state, systems, positions, nc_filename, **{})
    replica_exchange.number_of_iterations = 2000
    replica_exchange.run()

    u_permuted = replica_exchange.database.ncfile.variables["energies"][:]
    s = replica_exchange.database.ncfile.variables["states"][:]
    u = permute_energies(u_permuted, s)

    beta = (state.temperature * kB) ** -1.
    u0 = np.array([[testsystems.PowerOscillator.reduced_potential(beta, ho2.K, ho2.b, ho.K, ho.b) for ho in oscillators] for ho2 in oscillators])

    l = np.log(u.mean(0))
    l0 = np.log(u0)

    eq(l0, l, decimal=1)

def test_hrex_save_and_load():

    nc_filename = tempfile.mkdtemp() + "/out.nc"

    temperature = 1 * unit.kelvin

    K0 = 100.0  # Units are automatically added by the testsystem
    K = [K0, K0 * 10., K0 * 1.]
    powers = [2., 2., 4.]
    n_replicas = len(K)

    oscillators = [testsystems.PowerOscillator(b=powers[i]) for i in range(n_replicas)]

    systems = [ho.system for ho in oscillators]
    positions = [ho.positions for ho in oscillators]

    state = ThermodynamicState(system=systems[0], temperature=temperature)

    replica_exchange = hamiltonian_exchange.HamiltonianExchange.create_repex(state, systems, positions, nc_filename, **{})
    replica_exchange.number_of_iterations = 200
    replica_exchange.run()

    
    replica_exchange = hamiltonian_exchange.HamiltonianExchange.resume_repex(nc_filename)
    eq(replica_exchange.iteration, 200)
    replica_exchange.number_of_iterations = 300
    replica_exchange.run()