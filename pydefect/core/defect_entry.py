# -*- coding: utf-8 -*-

import itertools
import json
import os
import ruamel.yaml as yaml

from pymatgen.core.structure import Structure
from pymatgen.core.composition import Composition

from monty.json import MontyEncoder
from monty.serialization import loadfn


__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2017, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "December 4, 2017"


def get_num_atoms_for_elements(structure):
    """
    Return numbers of ions for elements in a structure.
    Example: Al1Mg31O32
        return: [1, 31, 32]
    """
    symbol_list = [site.specie.symbol for site in structure]
    return [len(tuple(a[1])) for a in itertools.groupby(symbol_list)]


def element_diff_from_poscar_files(poscar1, poscar2):
    c1 = Composition(
        Structure.from_file(poscar1).composition, allow_negative=True)
    c2 = Composition(
        Structure.from_file(poscar2).composition, allow_negative=True)
    c_diff = c1 - c2
    return {str(e): int(c_diff[e]) for e in c_diff}


class DefectEntry:
    """
    This class object holds all the information related to initial setting of a
    single defect.
    Args:
        name (str):
            Name of a defect without charge. This is used when analyzing defect
            formation energy.
        initial_structure (Structure):
            Structure with a defect before the structure optimization.
        removed_atoms (dict):
            Keys: Atom indices removed from the perfect supercell.
                  The index begins from 0.
                  For interstitials, set {}.
            Values: DefectSupercell coordinates
        inserted_atoms (list):
            Atom indices inserted in the supercell after removing atoms.
            The index begins from 0.
            For vacancies, set [].
        element_diff (dict):
            Keys: Element names
            Values: Change of the numbers of elements wrt perfect supercell.
        charge (int):
            Charge state of the defect
    """
    def __init__(self, name, initial_structure, removed_atoms, inserted_atoms,
                 element_diff, charge):
        self._name = name
        self._initial_structure = initial_structure
        self._removed_atoms = removed_atoms
        self._inserted_atoms = inserted_atoms
        self._element_diff = element_diff
        self._charge = charge

    def __eq__(self, other):
        if other is None or type(self) != type(other):
            raise TypeError
        return self.as_dict() == other.as_dict()

    @classmethod
    def from_dict(cls, d):
        """
        Constructs a DefectEntry class object from a dictionary.
        """
        # The keys need to be converted to integers.
        removed_atoms = {int(k): v for k, v in d["removed_atoms"].items()}
#        inserted_atoms = {int(k): v for k, v in d["inserted_atoms"].items()}
        element_diff = \
            {k: int(v) for k, v in d["element_diff"].items()}

        return cls(d["name"], d["initial_structure"], removed_atoms,
                   d["inserted_atoms"], element_diff, d["charge"])

    # TODO: get removed_atoms and inserted_atoms by comparing initial_structure
    #       and perfect_structure
    @classmethod
    def from_yaml(cls, filename):
        """
        An example of yaml file.
            name: Va_O1
            initial_structure: POSCAR
            perfect_structure: ../perfect/POSCAR
            removed_atoms: {32: [0.25, 0.25, 0.25]}
            inserted_atoms: !!null
            charge: 2
        """

        abs_dir = os.path.split(os.path.abspath(filename))[0]

        with open(filename, "r") as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)

        element_diff = element_diff_from_poscar_files(
            os.path.join(abs_dir, yaml_data["initial_structure"]),
            os.path.join(abs_dir, yaml_data["perfect_structure"]))

        s = Structure.from_file(os.path.join(abs_dir,
                                             yaml_data["initial_structure"]))

        return cls(yaml_data["name"], s, yaml_data["removed_atoms"],
                   yaml_data["inserted_atoms"], element_diff,
                   yaml_data["charge"])

    @classmethod
    def json_load(cls, filename):
        """
        Constructs a DefectEntry class object from a json file.
        """
        return cls.from_dict(loadfn(filename))

    @property
    def name(self):
        return self._name

    @property
    def initial_structure(self):
        return self._initial_structure

    @property
    def removed_atoms(self):
        return self._removed_atoms

    @property
    def inserted_atoms(self):
        return self._inserted_atoms

    @property
    def element_diff(self):
        return self._element_diff

    @property
    def charge(self):
        return self._charge

    @property
    def atom_mapping_to_perfect(self):
        """
        Returns a list of atom mapping from defect structure to perfect.
        Example of Mg32O32 supercell:
            When 33th atom, namely first O, is removed,
                mapping = [0, 1, 2, .., 31, 33, 34, .., 62]
                len(mapping) = 63

        """
        total_nions = (sum(get_num_atoms_for_elements(self._initial_structure))
                       - len(self._inserted_atoms)
                       + len(self._removed_atoms))

        # initial atom mapping.
        mapping = list(range(total_nions))

        for o in sorted(self._removed_atoms.keys(), reverse=True):
            mapping.pop(o)

        for i in sorted(self._inserted_atoms, reverse=True):
            mapping.insert(i, None)

        return mapping

    def as_dict(self):
        """
        Dict representation of DefectInput class object.
        """
        d = {"name": self._name,
             "initial_structure": self._initial_structure,
             "removed_atoms": self._removed_atoms,
             "inserted_atoms": self._inserted_atoms,
             "element_diff": self._element_diff,
             "charge": self._charge}
        return d

    def to_json_file(self, filename):
        """
        Returns a json file.
        """
        with open(filename, 'w') as fw:
            json.dump(self.as_dict(), fw, indent=2, cls=MontyEncoder)

    # TODO: remove bugs below
    # def anchor_atom_index(self):
    #     """
    #     Returns an index of atom that is the farthest from the defect.
    #     This atom is assumed not to displace during the structure
    #     optimization, and so used for analyzing local defect structure.
    #     """
        # radius = max(self._initial_structure.lattice.abc) * 2
        # num_sites = len(self._initial_structure.sites)
        # shortest_distances = np.full(num_sites, radius, dtype=float)

        # distance_set = self._initial_structure.get_sites_in_sphere(
        #     self._defect_coords, radius, include_index=True)

        # for d in distance_set:
        #     atom_index = d[2]
        #     if d[1] < shortest_distances[atom_index]:
        #         shortest_distances[atom_index] = d[1]

        # farthest_atom_index = np.argmax(shortest_distances)
        # farthest_dist = shortest_distances[farthest_atom_index]

        # return farthest_atom_index, farthest_dist
