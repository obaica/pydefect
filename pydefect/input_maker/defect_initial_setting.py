# -*- coding: utf-8 -*-
from collections import defaultdict
import json


from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from monty.json import MontyEncoder, MSONable
from monty.serialization import loadfn, dumpfn

from obadb.util.structure_handler import get_symmetry_dataset, \
    get_point_group_from_dataset, get_coordination_distances

from pydefect.core.error_classes import InvalidInputFileError
from pydefect.database.atom import electronegativity_list, charge
from pydefect.util.logger import get_logger
from pydefect.core.irreducible_site import IrreducibleSite
from pydefect.core.config \
    import ELECTRONEGATIVITY_DIFFERENCE, DISPLACEMENT_DISTANCE, CUTOFF_RADIUS, \
    SYMMETRY_TOLERANCE, ANGLE_TOL

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"

logger = get_logger(__name__)


def electronegativity_not_defined(a, b):
    logger.warning("Electronegativity of {} and/or {} not defined".format(a, b))


def extended_range(i):
    """
    Extended range method used for positive/negative input value.
    The input value is included for both positive and negative numbers.
    E.g., extended_range(3) = [0, 1, 2, 3]
          extended_range(-3) = [-3, -2, -1, 0]

    Args:
        i (int): an integer
    """
    if isinstance(i, int):
        return range(i + 1) if i >= 0 else range(i, 1)
    else:
        raise AttributeError


def get_electronegativity(element):
    try:
        return electronegativity_list[element]
    except KeyError:
        logger.warning("Electronegativity of " + element + " is unavailable, " +
                       "so set to 0.")
        return 0


def get_oxidation_state(element):
    try:
        return charge[element]
    except KeyError:
        logger.warning("Oxidation state of " + element + " is unavailable," +
                       "so set to 0.")
        return 0


def print_dopant_info(dopant):
    """ Print dopant info.
    This method is used to add dopant info a posteriori.
    Args:
        dopant (str): Dopant element name e.g., Mg
    """
    if Element.is_valid_symbol(dopant):
        electronegativity = get_electronegativity(dopant)
        oxidation_state = get_oxidation_state(dopant)

        print("   Dopant element: {}".format(dopant))
        print("Electronegativity: {}".format(electronegativity))
        print("  Oxidation state: {}".format(oxidation_state))
    else:
        logger.warnings(dopant + " is not a proper element name.")


def get_distances(string):
    distances = {}
    key = None
    # string = "Mg: 2.1 2.2 O: 2.3 2.4".split()
    #          -> {"Mg": [2,1, 2.2], "O": [2.3, 2.4]
    for i in string:
        if i[-1] == ":":
            distances[i[:-1]] = []
            key = i[:-1]
        else:
            if key:
                distances[key].append(float(i))
            else:
                raise ValueError("Invalid string {} for creating displacement_distance list".
                                 format(string))
    return distances


class DefectInitialSetting(MSONable):
    """ Holds full information for creating a series of DefectEntry objects.
    """

    def __init__(self,
                 structure: Structure,
                 space_group_symbol: str,
                 transformation_matrix: list,
                 cell_multiplicity: int,
                 irreducible_sites: list,
                 dopant_configs: list,
                 antisite_configs: list,
                 interstitial_names: list,
                 included: list,
                 excluded: list,
                 displacement_distance: float,
                 cutoff: float,
                 symprec: float,
                 angle_tolerance: float,
                 oxidation_states: dict,
                 electronegativity: dict):
        """
        Args:
            structure (Structure):
                pmg Structure class object for perfect supercell
            space_group_symbol (str):
                space group symbol
            transformation_matrix (list):
                Diagonal component of transformation matrix.
                Now the unitcell is expanded w/o rotations, so non-diagonal
                components are zero.
            cell_multiplicity (int):
                How much is the supercell larger than the *primitive* cell.
                This is used for calculating the defect concentration.
                Note that (multiplicity of the symmetry) * cell_multiplicity
                is the number of irreducible sites in the supercell.
            irreducible_sites (list):
                List of IrreducibleSite class objects
            dopant_configs (Nx2 list):
                Dopant configurations, e.g., [["Al", Mg"], ["N", "O"]]
            antisite_configs (Nx2 list):
                Antisite configurations, e.g., [["Mg","O"], ["O", "Mg"]]
            interstitial_names (list):
                Interstitial site namea written in intersitital.in file
            included (list):
                Exceptionally added defects with charges,
                e.g., ["Va_O1_-1", "Va_O1_-2"]
            excluded (list):
                Exceptionally removed defects with charges. If they don't exist,
                this flag does nothing. e.g., ["Va_O1_1", "Va_O1_2"]
            displacement_distance (float):
                Maximum displacement in angstrom. 0 means random displacement is
                switched off.
            cutoff (float):
                Cutoff radius in which atoms are displaced.
            symprec (float):
                Precision used for symmetry analysis.
            angle_tolerance (float):
                Angle tolerance for symmetry analysis in degree
            oxidation_states (dict):
                Oxidation states for relevant elements. Used to determine the
                default defect charges.
            electronegativity (dict):
                Electronegativity for relevant elements. Used to determine the
                substitutional defects.
        """

        self.structure = structure
        self.space_group_symbol = space_group_symbol
        self.transformation_matrix = transformation_matrix
        self.cell_multiplicity = cell_multiplicity
        self.irreducible_sites = list(irreducible_sites)
        self.dopant_configs = list(dopant_configs)
        # dopant element names are derived from in_name of dopant_configs.
        self.dopants = set([d[0] for d in dopant_configs])
        self.antisite_configs = list(antisite_configs)
        self.interstitial_names = list(interstitial_names)
        self.included = list(included) if included else []
        self.excluded = list(excluded) if excluded else []
        self.displacement_distance = displacement_distance
        self.cutoff = cutoff
        self.symprec = symprec
        self.angle_tolerance = angle_tolerance
        self.oxidation_states = oxidation_states
        self.electronegativity = electronegativity

    @classmethod
    def from_dict(cls, d):
        # Expansion of irreducible_sites is necessary.
        irreducible_sites = []
        for i in d["irreducible_sites"]:
            irreducible_sites.append(IrreducibleSite.from_dict(i))

        structure = d["structure"]
        if isinstance(structure, dict):
            structure = Structure.from_dict(structure)

        return cls(structure=structure,
                   space_group_symbol=d["space_group_symbol"],
                   transformation_matrix=d["transformation_matrix"],
                   cell_multiplicity=d["cell_multiplicity"],
                   irreducible_sites=irreducible_sites,
                   dopant_configs=d["dopant_configs"],
                   antisite_configs=d["antisite_configs"],
                   interstitial_names=d["interstitial_names"],
                   included=d["included"],
                   excluded=d["excluded"],
                   displacement_distance=d["displacement_distance"],
                   cutoff=d["cutoff"],
                   symprec=d["symprec"],
                   angle_tolerance=d["angle_tolerance"],
                   oxidation_states=d["oxidation_states"],
                   electronegativity=d["electronegativity"])

    @classmethod
    def load_json(cls, filename):
        return loadfn(filename)

    @classmethod
    def from_defect_in(cls, poscar="DPOSCAR", defect_in_file="defect.in"):
        """
        Currently, the file format of defect.in is not flexible, so be careful
        when modifying it by hand. The first word is mostly parsed. The number
        of words for each tag and the sequence of information is assumed to be
        fixed. See manual with care.
        E.g.,
            Irreducible element: Mg1
               Equivalent atoms: 1..32
         Fractional coordinates: 0.0000000 0.0000000 0.0000000
              Electronegativity: 1.31
                Oxidation state: 2
        """
        structure = Structure.from_file(poscar)
        space_group_symbol = None
        irreducible_sites = []
        antisite_configs = []
        interstitial_names = []
        included = None
        excluded = None
        electronegativity = {}
        oxidation_states = {}
        dopant_configs = []
        distance = None
        cutoff = None
        symprec = None

        with open(defect_in_file) as di:
            for l in di:
                line = l.split()

                if not line:
                    continue
                elif line[0] == "Space":
                    space_group_symbol = line[2]
                elif line[0] == "Irreducible":
                    irreducible_name = line[2]
                    # remove index from irreducible_name, e.g., "Mg1" --> "Mg"
                    element = ''. \
                        join([i for i in irreducible_name if not i.isdigit()])
                    wyckoff = di.readline().split()[2]
                    site_symmetry = di.readline().split()[2]

                    coordination_distances = \
                        get_distances(di.readline().split()[1:])
                    first_index, last_index = \
                        [int(i) for i in di.readline().split()[2].split("..")]
                    representative_coords = \
                        [float(i) for i in di.readline().split()[2:]]
                    irreducible_sites.append(
                        IrreducibleSite(irreducible_name,
                                        element,
                                        first_index,
                                        last_index,
                                        representative_coords,
                                        wyckoff,
                                        site_symmetry,
                                        coordination_distances))
                    electronegativity[element] = float(di.readline().split()[1])
                    oxidation_states[element] = int(di.readline().split()[2])

                elif line[0] == "Interstitials:":
                        interstitial_names = list(line[1:])

                elif line[0] == "Antisite":
                    antisite_configs = [i.split("_") for i in line[2:]]

                elif line[0] == "Dopant":
                    d = line[2]
                    electronegativity[d] = float(di.readline().split()[1])
                    oxidation_states[d] = int(di.readline().split()[2])

                elif line[0] == "Substituted":
                    dopant_configs = [i.split("_") for i in line[2:]]

                elif line[0] == "Maximum":
                    distance = float(line[2])

                elif line[0] == "Cutoff":
                    cutoff = float(line[5])

                elif line[0] == "Symprec:":
                    symprec = float(line[1])

                elif line[0] == "Angle":
                    angle_tolerance = float(line[2])

                elif line[0] == "Exceptionally":
                    if line[1] == "included:":
                        included = line[2:]
                    elif line[1] == "excluded:":
                        excluded = line[2:]

                else:
                    raise InvalidInputFileError(
                        "{} is not supported in defect.in!".format(line))

        return cls(structure, space_group_symbol, irreducible_sites,
                   dopant_configs, antisite_configs, interstitial_names,
                   included, excluded, distance, cutoff, symprec,
                   angle_tolerance, oxidation_states, electronegativity)

    @classmethod
    def from_basic_settings(cls,
                            structure: Structure,
                            transformation_matrix: list,
                            cell_multiplicity: int,
                            dopants: list = None,
                            is_antisite: bool = True,
                            en_diff: float = ELECTRONEGATIVITY_DIFFERENCE,
                            included: list = None,
                            excluded: list = None,
                            distance: float = DISPLACEMENT_DISTANCE,
                            cutoff: float = CUTOFF_RADIUS,
                            symprec: float = SYMMETRY_TOLERANCE,
                            angle_tolerance: float = ANGLE_TOL,
                            interstitial_recommender: bool = False,
                            interstitial_in_file: str = None):
        """ Generates object with some default settings.

        Args:
            structure (Structure/IStructure):
                Structure used for supercell defect calculations
            transformation_matrix (list):
                Diagonal component of transformation matrix.
            cell_multiplicity (int):
                How much is the supercell larger than the *primitive* cell.
            dopants (list):
                Dopant element names, e.g., ["Al", "N"]
            is_antisite (bool):
                Whether to consider antisite defects.
            en_diff (float):
                Electronegativity (EN) difference for determining sets of
                antisites and dopant sites.
            included (list):
                Exceptionally added defects with charges,
                e.g., ["Va_O1_-1", "Va_O1_-2"]
            excluded (list):
                Exceptionally removed defects with charges. If they don't exist,
                this flag does nothing. e.g., ["Va_O1_1", "Va_O1_2"]
            distance (float):
                Maximum displacement displacement_distance in angstrom. 0 means that random
                displacement is not considered.
            cutoff (float):
                Cutoff radius in which atoms are displaced.
            symprec (float):
                Distance precision used for symmetry analysis.
            angle_tolerance (float):
                Angle precision used for symmetry analysis.
            interstitial_recommender (list):
                The recommender name for interstitial sites.
            interstitial_in_file (str):
                Name of interstitial.in file.
        """
        if dopants is None:
            dopants = []
        s = structure.get_sorted_structure()

        space_group_analyzer = \
            SpacegroupAnalyzer(s, symprec=symprec,
                               angle_tolerance=angle_tolerance)
        symmetrized_structure = space_group_analyzer.get_symmetrized_structure()

        space_group_symbol = space_group_analyzer.get_space_group_symbol()

        symbol_set = s.symbol_set
        dopant_symbol_set = tuple(dopants)
        element_set = symbol_set + dopant_symbol_set

        # Electronegativity and oxidation states for constituents and dopants
        electronegativity = {}
        oxidation_states = {}
        for element in element_set:
            electronegativity[element] = get_electronegativity(element)
            oxidation_states[element] = get_oxidation_state(element)

        # num_irreducible_sites["Mg"] = 2 means Mg has 2 inequivalent sites
        num_irreducible_sites = defaultdict(int)

        # irreducible_sites (list): a set of IrreducibleSite class objects
        irreducible_sites = []

        # equivalent_sites: Equivalent site indices from SpacegroupAnalyzer.
        equiv_sites = symmetrized_structure.equivalent_sites
        last_index = 0

        lattice = symmetrized_structure.lattice.matrix
        sym_dataset = get_symmetry_dataset(symmetrized_structure, symprec,
                                           angle_tolerance)

        for i, equiv_site in enumerate(equiv_sites):
            # set element name of equivalent site
            element = equiv_site[0].species_string

            # increment number of inequivalent sites for element
            num_irreducible_sites[element] += 1

            first_index = last_index + 1
            last_index = last_index + len(equiv_site)
            # the following np.array type must be converted to list
            # to keep the consistency of the IrreducibleSite object.
            representative_coords = list(equiv_site[0].frac_coords)
            irreducible_name = element + str(num_irreducible_sites[element])
            wyckoff = sym_dataset["wyckoffs"][first_index]

            simplified_point_group = \
                get_point_group_from_dataset(sym_dataset, representative_coords,
                                             lattice, symprec)[0]
            coordination_distances = \
                get_coordination_distances(symmetrized_structure, first_index)

            irreducible_sites.append(IrreducibleSite(irreducible_name,
                                                     element,
                                                     first_index,
                                                     last_index,
                                                     representative_coords,
                                                     wyckoff,
                                                     simplified_point_group,
                                                     coordination_distances))

        # E.g., antisite_configs = [["Mg, "O"], ...]
        antisite_configs = []
        if is_antisite is True:
            for elem1 in symbol_set:
                for elem2 in symbol_set:
                    if elem1 == elem2:
                        continue
                    elif elem1 in electronegativity and \
                            elem2 in electronegativity:
                        if abs(electronegativity[elem1] -
                               electronegativity[elem2]) < en_diff:
                            antisite_configs.append([elem1, elem2])
                    else:
                        electronegativity_not_defined(elem1, elem2)

        # E.g., dopant_configs = [["Al", "Mg"], ...]
        dopant_configs = []
        for dopant in dopants:
            if dopant in symbol_set:
                logger.warning("Dopant " + dopant + " constitutes host.")
                continue
            for elem in symbol_set:
                if elem in electronegativity and dopant in electronegativity:
                    if abs(electronegativity[elem] -
                           electronegativity[dopant]) < en_diff:
                        dopant_configs.append([dopant, elem])
                else:
                    electronegativity_not_defined(dopant, elem)

        if interstitial_recommender:
            # TODO: Implement the interstitial construction and write down
            #  interstitial.in.
            interstitial_names = []
        else:
            interstitial_names = []

        return cls(symmetrized_structure, space_group_symbol,
                   transformation_matrix, cell_multiplicity, irreducible_sites,
                   dopant_configs, antisite_configs, interstitial_names,
                   included, excluded, distance, cutoff, symprec,
                   angle_tolerance, oxidation_states, electronegativity)

    def as_dict(self):
        d = {"@module":               self.__class__.__module__,
             "@class":                self.__class__.__name__,
             "structure":             self.structure,
             "space_group_symbol":    self.space_group_symbol,
             "transformation_matrix": self.transformation_matrix,
             "cell_multiplicity":     self.cell_multiplicity,
             "irreducible_sites":    [i.as_dict()
                                       for i in self.irreducible_sites],
             "dopant_configs":        self.dopant_configs,
             "antisite_configs":      self.antisite_configs,
             "interstitial_names":     self.interstitial_names,
             "included":              self.included,
             "excluded":              self.excluded,
             "displacement_distance": self.displacement_distance,
             "cutoff":                self.cutoff,
             "symprec":               self.symprec,
             "angle_tolerance":       self.angle_tolerance,
             "oxidation_states":      self.oxidation_states,
             "electronegativity":     self.electronegativity}

        return d

    def to_yaml_file(self, filename="defect.yaml"):
        dumpfn(self.as_dict(), filename)

    def to_json_file(self, filename):
        with open(filename, 'w') as fw:
            json.dump(self.as_dict(), fw, indent=2, cls=MontyEncoder)

    def to(self, defect_in_file="defect.in", poscar_file="DPOSCAR"):
        """ Prints readable defect.in file.
        """
        self._write_defect_in(defect_in_file)
        self.structure.to(fmt="poscar", filename=poscar_file)

    def make_defect_name_set(self):
        """ Returns a set of defect names by default.
        """
        name_set = list()

        # Vacancies
        # Charges are set from 0 to minus of the oxidation state.
        for i in self.irreducible_sites:
            os = self.oxidation_states[i.element]
            for o in extended_range(-os):
                name_set.append("Va_" + i.irreducible_name + "_" + str(o))

        # Interstitials
        # Both intrinsic elements and dopants are considered.
        # Charges are set from 0 to the oxidation state.
        inserted_elements = \
            tuple(self.structure.symbol_set) + tuple(self.dopants)
        for e in inserted_elements:
            for o in extended_range(self.oxidation_states[e]):
                for name in self.interstitial_names:
                    name_set.append(e + "_" + name + "_" + str(o))

        # Antisites + Substituted dopants
        for in_elem, out_elem in self.antisite_configs + self.dopant_configs:
            for i in self.irreducible_sites:
                if out_elem == i.element:
                    os_diff = self.oxidation_states[in_elem] - \
                              self.oxidation_states[out_elem]
                    for o in extended_range(os_diff):
                        name_set.append(
                            in_elem + "_" + i.irreducible_name + "_" + str(o))

        for i in self.included:
            if i not in name_set:
                name_set.append(i)
            else:
                logger.warning("{} *included*, but already exists.".format(e))

        for e in self.excluded:
            if e in name_set:
                name_set.remove(e)
            else:
                logger.warning("{} *excluded*, but does not exist.".format(e))

        return name_set

    def _write_defect_in(self, defect_in_file="defect.in"):
        """ Helper method to write down defect.in file.

        Args:
            defect_in_file (str):
                Name of defect.in type file.
        """
        lines = list()
        lines.append("  Space group: {}\n".format(self.space_group_symbol))

        lines.append("Transformation matrix: {0[0]:2d} {0[1]:2d} {0[2]:2d}".
                     format(self.transformation_matrix))

        lines.append("Cell multiplicity: {}\n".format(self.cell_multiplicity))

        for e in self.irreducible_sites:
            lines.append("   Irreducible element: {}".format(
                e.irreducible_name))
            lines.append("        Wyckoff letter: {}".format(
                e.wyckoff))
            lines.append("         Site symmetry: {}".format(
                e.site_symmetry))
            c = ""
            for k, v in e.coordination_distances.items():
                c += k + ": " + " ".join([str(round(i, 2)) for i in v]) + " "
            lines.append("          Coordination: {}".format(c))
            lines.append("      Equivalent atoms: {}".format(
                str(e.first_index) + ".." + str(e.last_index)))
            lines.append("Fractional coordinates: %9.7f  %9.7f  %9.7f" %
                         tuple(e.representative_coords))
            lines.append("     Electronegativity: {}".format(
                self.electronegativity[e.element]))
            lines.append("       Oxidation state: {}\n".format(
                self.oxidation_states[e.element]))

        lines.append("Interstitials: " + " ".join(self.interstitial_names))

        if self.antisite_configs is not []:
            lines.append("Antisite defects: " +
                         ' '.join(i[0] + "_" + i[1]
                                  for i in self.antisite_configs)
                         + "\n")

        for d in self.dopants:
            if d not in self.structure.symbol_set:
                lines.append("   Dopant element: {}".format(d))
                lines.append("Electronegativity: {}".format(
                    self.electronegativity[d]))
                lines.append("  Oxidation state: {}\n".format(
                    self.oxidation_states[d]))

        lines.append("Substituted defects: " +
                     ' '.join(i[0] + "_" + i[1] for i in self.dopant_configs)
                     + "\n")

        lines.append("Maximum Displacement: {}\n".
                     format(self.displacement_distance))

        lines.append("Exceptionally included: " +
                     ' '.join(i for i in self.included))
        lines.append("Exceptionally excluded: " +
                     ' '.join(i for i in self.excluded) + "\n")

        lines.append(
            "Cutoff region of atoms perturbed: {}".format(self.cutoff))
        lines.append("Symprec: {}".format(self.symprec))
        lines.append("Angle tolerance: {}\n".format(self.angle_tolerance))

        with open(defect_in_file, 'w') as di:
            di.write("\n".join(lines))


