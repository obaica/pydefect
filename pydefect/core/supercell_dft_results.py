# -*- coding: utf-8 -*-

from itertools import product
import json
import numpy as np
import os
import warnings

from monty.json import MontyEncoder
from monty.serialization import loadfn

from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.outputs import Outcar, Vasprun
from pymatgen.electronic_structure.core import Spin

from pydefect.core.defect_entry import DefectEntry

__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2017, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "December 4, 2017"


def defect_center(defect_entry, structure=None):
    """
    Returns a fractional coordinates of the defect center which is
    calculated by averaging the coordinates of vacancies and interstitials.
    If len(defect_coords) == 1, returns defect_coords[0].

    Args:
        structure (Structure):
        defect_entry (DefectEntry): related DefectEntry class object
    """
    # If structure is not given, initial_structure of defect_entry is used.
    if structure is None:
        structure = defect_entry.initial_structure

    inserted_atom_coords = list([structure.frac_coords[k]
                                 for k in defect_entry.inserted_atoms])
    removed_atom_coords = list(defect_entry.removed_atoms.values())

    defect_coords = inserted_atom_coords + removed_atom_coords

    # np.array([[0, 0.1, 0.2], [0.3, 0.4, 0.5]]).transpose() =
    # np.array([[0, 0.3], [0.1, 0.4], [0.2, 0.5]])
    return [np.mean(i) for i in np.array(defect_coords).transpose()]


def min_distance_under_pbc(frac1, frac2, lattice_vector_matrix):
    """
    Return the shortest distance between two points in fractional coordinates
    under periodic boundary condition.

    Args:
       frac1 (1x3 list): fractional coordinates
       frac2 (1x3 list): fractional coordinates
       lattice_vector_matrix (3x3 numpy array): a, b, c lattice vectors
    """

    candidate = []
    frac = np.dot(lattice_vector_matrix, frac2 - frac1)

    for index in product((-1, 0, 1), repeat=3):
        index = np.array(index)
        delta_frac = np.dot(lattice_vector_matrix, index)
        distance = np.linalg.norm(delta_frac + frac)
        candidate.append(distance)

    return min(candidate)


def distance_list(structure, coords):
    """
    Returns a list of the shortest distances between a point and atoms in
    structure under periodic boundary condition.
    Args:
       structure (Structure): pmg structure class object
       coords (1x3 numpy array): fractional coordinates
    """

    lattice_vector_matrix = structure.lattice.matrix

    return [min_distance_under_pbc(host, coords, lattice_vector_matrix)
            for host in structure.frac_coords]


def distances_from_point(structure, defect_entry):
    """
    Returns a list of distances at atomic sites from a defect center defined
    by defect_entry. Note that in the case of an interstitial-type defect,
    zero is also set.

    Args:
        structure (Structure):
        defect_entry (DefectEntry): related DefectEntry class object
    """
    return distance_list(structure, defect_center(defect_entry, structure))


class SupercellDftResults:
    """
    A class holding DFT results for supercell systems both w/ and w/o a defect.
    """

    def __init__(self, final_structure, total_energy, eigenvalues,
                 electrostatic_potential):
        self._final_structure = final_structure
        self._total_energy = total_energy
        self._eigenvalues = eigenvalues
        self._electrostatic_potential = electrostatic_potential

    def __str__(self):
        outs = ["total energy:" + str(self._total_energy),
                "electrostatic potential:" + str(self._electrostatic_potential),
                "eigenvalues:" + str(self._eigenvalues),
                "final structure: \n" + str(self._final_structure)]
        return "\n".join(outs)

    @classmethod
    def from_vasp_files(cls, directory_path, contcar_name="CONTCAR",
                        outcar_name="OUTCAR", vasprun_name="vasprun.xml"):
        """
        Although electrostatic_potential is not used for UnitcellDftResults,
        this method is implemented in DftResults class because constructor is
        easily written.

        Args:
            directory_path (str): path of directory.
            contcar_name (str): Name of converged CONTCAR file.
            outcar_name (str): Name of OUTCAR file.
            vasprun_name (str): Name of vasprun.xml file.
        """
        contcar = Poscar.from_file(os.path.join(directory_path, contcar_name))
        outcar = Outcar(os.path.join(directory_path, outcar_name))
        vasprun = Vasprun(os.path.join(directory_path, vasprun_name))

        # TODO: check if the structure optimization is finished or not
        final_structure = contcar.structure
        total_energy = outcar.final_energy
        eigenvalues = vasprun.eigenvalues
        electrostatic_potential = outcar.electrostatic_potential

        return cls(final_structure, total_energy, eigenvalues,
                   electrostatic_potential)

    @classmethod
    def from_dict(cls, d):
        """
        Constructs a class object from a dictionary.
        """
        eigenvalues = {}
        # Programmatic access to enumeration members in Enum class.
        for spin, v in d["eigenvalues"].items():
            eigenvalues[Spin(int(spin))] = np.array(v)

        return cls(d["final_structure"], d["total_energy"], eigenvalues,
                   d["electrostatic_potential"])

    @classmethod
    def json_load(cls, filename):
        """
        Constructs a class object from a json file.
        """
        return cls.from_dict(loadfn(filename))

    def as_dict(self):
        """
        Dict representation of DefectInitialSetting class object.
        Json-serializable dict representation.
        """
        # Spin object must be converted to string for to_json_file.
        eigenvalues = {str(spin): v.tolist()
                       for spin, v in self._eigenvalues.items()}

        d = {"final_structure":         self._final_structure,
             "total_energy":            self._total_energy,
             "eigenvalues":             eigenvalues,
             "electrostatic_potential": self._electrostatic_potential}

        return d

    def to_json_file(self, filename):
        """
        Returns a json file, named dft_results.json.
        """
        with open(filename, 'w') as fw:
            json.dump(self.as_dict(), fw, indent=2, cls=MontyEncoder)

    @property
    def eigenvalues(self):
        return self._eigenvalues

    @property
    def final_structure(self):
        return self._final_structure

    @property
    def total_energy(self):
        return self._total_energy

    @property
    def electrostatic_potential(self):
        return self._electrostatic_potential

    def relative_total_energy(self, perfect_dft_results):
        """
        Return relative total energy w.r.t. the perfect supercell.

        Args:
            perfect_dft_results (SupercellDftResults):
                SupercellDftResults class object for the perfect supercell.
        """
        return self._total_energy - perfect_dft_results.total_energy

    def relative_potential(self, perfect_dft_results, defect_entry):
        """
        Return a list of relative site potential w.r.t. the perfect supercell.
        Note that None is inserted for interstitial sites.

        Args:
            perfect_dft_results (SupercellDftResults):
                SupercellDftResults class object for the perfect supercell.
            defect_entry (DefectEntry):
                DefectEntry class object.
        """
        mapping = defect_entry.atom_mapping_to_perfect

        relative_potential = []

        for d_atom, p_atom in enumerate(mapping):

            if p_atom is None:
                relative_potential.append(None)
            else:
                ep_defect = self.electrostatic_potential[d_atom]
                ep_perfect = perfect_dft_results.electrostatic_potential[p_atom]
                relative_potential.append(ep_defect - ep_perfect)

        return relative_potential

#    def inserted_atom_displacements(self, defect_entry):
#        """
#        Returns coordinates of defect center by calculating the averaged
#        coordinates. If len(defect_coords) == 1, returns defect_coords[0].
#        Args:
#            defect_entry (DefectEntry):
#                related DefectEntry class object
#        """
#        displacements = []
#
#        for k in defect_entry.inserted_atoms.keys:
#            before_relaxation = defect_entry.initial_structure.frac_coords[k]
#            after_relaxation = self.final_structure.frac_coords[k]
#            displacements.append(
#                min_distance_and_its_v2coord(before_relaxation,
#                                             after_relaxation,
#                                             self.final_structure.axis))
#        return displacements


def main():
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--dirs", dest="dirs", nargs="+", type=str,
                        help="Directory names.")
    parser.add_argument("--dir_all", dest="dir_all", action="store_true",
                        help="Make dft_results.json for *[0-9] and perfect directory.")
    opts = parser.parse_args()

    if opts.dir_all:
        from glob import glob
        dirs = glob('*[0-9]/')
        dirs.append("perfect")
    else:
        dirs = opts.dirs

    for d in dirs:
        print(d)
        if os.path.isdir(d):
            try:
                dft_results = SupercellDftResults.\
                    from_vasp_files(d, contcar_name="CONTCAR",
                                    outcar_name="OUTCAR",
                                    vasprun_name="vasprun.xml")
                dft_results.to_json_file(
                    filename=os.path.join(d, "dft_results.json"))
            except:
                warnings.warn(message="Parsing data in " + d + " is failed.")
        else:
            warnings.warn(message=d + " does not exist, so nothing is done.")


if __name__ == "__main__":
    main()