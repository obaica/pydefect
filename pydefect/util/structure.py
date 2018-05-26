# -*- coding: utf-8 -*-

from collections import OrderedDict

import seekpath
import spglib
from pymatgen import Structure

from pydefect.database.atom import symbols_to_atom
from pydefect.util.math import normalized_random_3d_vector, random_vector

__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2018, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "April 4, 2018"


def structure_to_spglib_cell(structure):
    """
    Returns a *cell* tuple parsed by spglib that is composed of lattice
    parameters, atomic positions in fractional coordinates, and corresponding
    atomic numbers.
    Args:
        structure (Structure): Pymatgen Structure class object
    """
    lattice = list(structure.lattice.matrix)
    positions = structure.frac_coords.tolist()
    atomic_numbers = [i.specie.number for i in structure.sites]
    return lattice, positions, atomic_numbers


def spglib_cell_to_structure(cell):
    """
    Returns a pymatgen Structure class object from spglib cell tuple.
    Args:
        cell (3 tuple): Lattice parameters, atomic positions in fractional
                        coordinates, and corresponding
    """
    species = [symbols_to_atom[i] for i in cell[2]]
    return Structure(cell[0], species, cell[1])


def find_equivalent_sites(structure, symprec=0.01, angle_tolerance=5):
    """
    Returns an ordered structure and equivalent atom indices.
    Args:
        structure (Structure): Pymatgen Structure class object
        atom indices (list):
    """
    cell = structure_to_spglib_cell(structure)
    symmetry_dataset = \
        spglib.get_symmetry_dataset(cell=cell, symprec=symprec,
                                    angle_tolerance=angle_tolerance)
    # simple list, e.g., [0, 0, 1, 1, 2, 2,..]
#    mapping_to_primitive = symmetry_dataset["std_mapping_to_primitive"]
    mapping_to_primitive = symmetry_dataset["mapping_to_primitive"]
    print(mapping_to_primitive)

    primitive_cell = spglib.find_primitive(cell=cell, symprec=symprec,
                                           angle_tolerance=angle_tolerance)
    # simple list, e.g., [0, 0, 1, 1, 2, 2,..]
    primitive_equivalent_sites = \
        spglib.get_symmetry_dataset(cell=primitive_cell, symprec=symprec,
                                    angle_tolerance=angle_tolerance)["equivalent_atoms"]

    # {0:[0, 1], 1:[2, 3], 3:[4, 5], ..}
    print(primitive_equivalent_sites)
    mapping_to_primitive_dict = OrderedDict()
    for s_atom_index, p_atom_index in enumerate(mapping_to_primitive):
        if p_atom_index not in mapping_to_primitive_dict.keys():
            mapping_to_primitive_dict[p_atom_index] = [s_atom_index]
        else:
            mapping_to_primitive_dict[p_atom_index].append(s_atom_index)

    print(primitive_equivalent_sites)
    # {0:[0, 1], 1:[2, 3], 2:[4, 5], ..}
    equivalent_atoms = OrderedDict()
    for p_atom_index, inequiv_atom_index in enumerate(primitive_equivalent_sites.tolist()):

        if inequiv_atom_index not in equivalent_atoms.keys():
            equivalent_atoms[inequiv_atom_index] = []

        if p_atom_index in mapping_to_primitive_dict.keys():
            equivalent_atoms[inequiv_atom_index].\
                    extend(mapping_to_primitive_dict[p_atom_index])

    sites = []
    repr_sites_indices = []
    print(equivalent_atoms)
    for v in equivalent_atoms.values():
        repr_sites_indices.append(v[0])
        for i in v:
#            print(i)
            sites.append(structure.sites[i])

    ordered_structure = structure.from_sites(sites)

    return ordered_structure, equivalent_atoms, repr_sites_indices


def find_spglib_standard_primitive(structure, symprec=1e-05):
    """
    Returns a primitive unit cell.
    Args:
        structure (Structure): Pymatgen Structure class object
        symprec (float): distance tolerance in cartesian coordinates
                         Unit is compatible with the cell.
    """
    cell = structure_to_spglib_cell(structure)
    return spglib_cell_to_structure(spglib.find_primitive(cell, symprec))


def find_hpkot_primitive(structure, symprec=1e-05, angle_tolerance=-1.0):
    """
    Returns a hpkot primitive unit cell.
    Args:
        structure (Structure): Pymatgen Structure class object
        symprec (float): distance tolerance in cartesian coordinates
                         Unit is compatible with the cell.
        angle_tolerance (float): angle tolerance used for symmetry analysis.
    """
    cell = structure_to_spglib_cell(structure)
    res = seekpath.get_explicit_k_path(structure=cell, symprec=symprec,
                                       angle_tolerance=angle_tolerance)

    return seekpath_to_hpkot_structure(res)


def structure_to_seekpath(structure, time_reversal=True, ref_distance=0.025,
                          recipe='hpkot', threshold=1.e-7, symprec=1e-05,
                          angle_tolerance=-1.0):
    """
    Returns the full information for the band path of the given Structure class
    object generated by seekpath.
    Args:
        structure (Structure): Pymatgen Structure class object
        time_reversal (bool): If the time reversal symmetry exists
        ref_distance (float): distance for the k-point mesh.
        threshold (float): to use to verify if we are in edge case
                          (see seekpath)
        symprec (float): distance tolerance in cartesian coordinates
                         Unit is compatible with the cell.
        angle_tolerance (float): angle tolerance used for symmetry analysis.
    """
    cell = structure_to_spglib_cell(structure)
    res = seekpath.get_explicit_k_path(cell,
                                       with_time_reversal=time_reversal,
                                       reference_distance=ref_distance,
                                       recipe=recipe,
                                       threshold=threshold,
                                       symprec=symprec,
                                       angle_tolerance=angle_tolerance)

    # If numpy.allclose is too strict in pymatgen.core.lattice __eq__,
    # make almost_equal
    if structure.lattice == seekpath_to_hpkot_structure(res).lattice:
        return res
    else:
        raise NotStandardizedPrimitiveError(
            "The given structure is not standardized primitive cell.")


def seekpath_to_hpkot_structure(res):
    """
    Returns a pymatgen Structure class object from seekpath res dictionary.
    Args:
        res (dict): seekpath res dictionary.
    """
    lattice = res["primitive_lattice"]
    element_types = res["primitive_types"]
    species = [symbols_to_atom[i] for i in element_types]
    positions = res["primitive_positions"]
    return Structure(lattice, species, positions)


def perturb_neighbors(structure, center, cutoff, distance):
    """
    Returns the structure with randomly perturbed atoms near the input point in
    structure.

    Args:
        structure (Structure): pmg Structure/IStructure class object
        center (3x1 array): Fractional coordinates of a central position.
        cutoff (float): Radius of a sphere in which atoms are perturbed [A].
        distance (float): Max distance for the perturbation [A].
    """
    if type(center) == list and len(center) == 3:
        cartesian_coords = structure.lattice.get_cartesian_coords(center)
        neighbors = structure.get_sites_in_sphere(
            cartesian_coords, cutoff, include_index=True)
    else:
        raise ValueError

    sites = []
    # Since translate_sites accepts only one vector, we need to iterate this.
    for i in neighbors:
        vector = random_vector(normalized_random_3d_vector(), distance)
        site = i[2]
        sites.append(site)
        structure.translate_sites(site, vector, frac_coords=False)

    return structure, sites


class NotStandardizedPrimitiveError(Exception):
    pass
