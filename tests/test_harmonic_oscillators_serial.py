import numpy as np
import simtk.unit as unit
from repex.thermodynamics import ThermodynamicState
from repex.replica_exchange import ReplicaExchange
from repex import testsystems
import tempfile
from mdtraj.testing import eq
from mdtraj.utils import ensure_type

def permute_energies(u0, s):
    """Re-order an observable u0 so that u[i, j, k] correponds to frame i, sampled from state j, evaluated in state k."""
    u0 = ensure_type(u0, 'float32', 3, "u0")
    n_iter, n_replicas, n_replicas = u0.shape
    s = ensure_type(s, "int", 2, "s", shape=(n_iter, n_replicas))
    
    u = np.zeros((n_iter, n_replicas, n_replicas))
    for i, si in enumerate(s):
        mapping = dict(zip(range(n_replicas), si))
        inv_map = {v:k for k, v in mapping.items()}
        si_inv = [inv_map[k] for k in range(n_replicas)]
        u[i] = u0[i, si_inv]
    
    return u

def test_harmonic_oscillators():
    """Test harmonic oscillator reduced potentials at temperatures 1K, 10K, 100K."""
    """Note: one should test with n_replicas >= 3 because permutation math
    is trivial for n = 2 (permutation = inverse(permutation))
    """

    nc_filename = tempfile.mkdtemp() + "/out.nc"

    T_min = 1.0 * unit.kelvin
    T_i = [T_min, T_min * 10., T_min * 100.]
    n_replicas = len(T_i)

    ho = testsystems.HarmonicOscillator()

    system = ho.system
    positions = ho.positions

    states = [ ThermodynamicState(system=system, temperature=T_i[i]) for i in range(n_replicas) ]

    coordinates = [positions] * n_replicas

    replica_exchange = ReplicaExchange.create_repex(states, coordinates, nc_filename, **{})
    replica_exchange.number_of_iterations = 1000
    replica_exchange.run()

    u_permuted = replica_exchange.database.ncfile.variables["energies"][:]
    s = replica_exchange.database.ncfile.variables["states"][:]

    u = permute_energies(u_permuted, s)

    u0 = np.array([[ho.get_reduced_potential_expectation(s0, s1) for s1 in states] for s0 in states])

    l0 = np.log(u0)  # Compare on log scale because uncertainties are proportional to values
    l1 = np.log(u.mean(0))
    eq(l0, l1, decimal=1)

