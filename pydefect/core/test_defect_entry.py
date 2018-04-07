import unittest

from pymatgen.io.vasp.inputs import Poscar

from core.defect_entry import *

__author__ = "Yu Kumagai"
__copyright__ = "Copyright 2017, Oba group"
__version__ = "0.1"
__maintainer__ = "Yu Kumagai"
__email__ = "yuuukuma@gmail.com"
__status__ = "Development"
__date__ = "December 4, 2017"

DEFAULT_POTCAR_DIR="/home/common/default_POTCAR"
TEST_DIRECTORY = "../examples/MgO"
DIRNAME_VAC = TEST_DIRECTORY + "/defects/Va_O1_2"
FILENAME_JSON_VAC = DIRNAME_VAC + "/defect_entry_Va_O1_2.json"


class DefectEntryTest(unittest.TestCase):

    def setUp(self):
        """ """
        initial_structure = Poscar.from_file(DIRNAME_VAC + "/POSCAR").structure
        removed_atoms = {8: [0.25, 0.25, 0.25]}
        inserted_atoms = {}
        changes_of_num_elements = {"O": -1}
        charge = 2

        self._MgO_Va_O1_2 = \
            DefectEntry(initial_structure, removed_atoms, inserted_atoms,
                        changes_of_num_elements, charge)

        initial_structure_complex = \
            Poscar.from_file(DIRNAME_VAC + "/POSCAR").structure
        removed_atoms_complex = {8: [0.25, 0.25, 0.25], 9: [0.25, 0.25, 0.75]}
        inserted_atoms_complex = {8: "Al"}
        changes_of_num_elements_complex = {"Mg": 1, "O": -2}
        charge_complex = 2

        self._MgO_complex = \
            DefectEntry(initial_structure_complex, removed_atoms_complex,
                        inserted_atoms_complex, changes_of_num_elements_complex,
                        charge_complex)

    def test_Dict(self):
        d = self._MgO_Va_O1_2.as_dict()
        MgO_Va_O1_2_from_dict = DefectEntry.from_dict(d)
        self.assertTrue(MgO_Va_O1_2_from_dict == self._MgO_Va_O1_2)

    def test_json(self):
        self._MgO_Va_O1_2.to_json_file(FILENAME_JSON_VAC)
        from_json = DefectEntry.json_load(FILENAME_JSON_VAC)
        self.assertTrue(from_json == self._MgO_Va_O1_2)

    def test_atom_mapping_to_perfect(self):
        expected = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15]
        actual = self._MgO_Va_O1_2.atom_mapping_to_perfect
        print(actual)
        self.assertTrue(actual == expected)

        expected = [0, 1, 2, 3, 4, 5, 6, 7, None, 10, 11, 12, 13, 14, 15]
        actual = self._MgO_complex.atom_mapping_to_perfect
        print(actual)
        self.assertTrue(actual == expected)


#    def test_anchor_atom_index(self):
#        print(self._MgO_Va_O1_2.anchor_atom_index())


if __name__ == "__main__":
    unittest.main()
