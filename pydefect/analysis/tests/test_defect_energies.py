# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from chempotdiag.chem_pot_diag import ChemPotDiag

from pydefect.analysis.defect_energies import DefectEnergies
from pydefect.util.tools import sanitize_keys_in_dict
from pydefect.analysis.defect import Defect
from pydefect.corrections.corrections import ExtendedFnvCorrection
from pydefect.core.supercell_calc_results import SupercellCalcResults
from pydefect.core.unitcell_calc_results import UnitcellCalcResults
from pydefect.core.defect_entry import DefectEntry

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"

test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        "test_files", "core")


class ConvertStrKeysTest(unittest.TestCase):

    d = {"Va_O1_0": {"0": {"null": 1.0}, "1": {"inward": 2.0}}}
    print(type(d["Va_O1_0"]))
    print(sanitize_keys_in_dict(d))


class DefectEnergiesTest(unittest.TestCase):

    def setUp(self):
        """ """
        unitcell_file = os.path.join(test_dir, "MgO/defects/unitcell.json")
        unitcell = UnitcellCalcResults.load_json(unitcell_file)
        perfect_file = os.path.join(test_dir,
                                    "MgO/defects/perfect/dft_results.json")
        perfect = SupercellCalcResults.load_json(perfect_file)

        defect_dirs = ["Mg_O1_0", "Mg_O1_1", "Mg_O1_2", "Mg_O1_3", "Mg_O1_4",
                       "Mg_i1_0", "Mg_i1_1", "Mg_i1_2", "Va_O1_2_inward", "Va_O1_1", "Va_O1_2",
                       "Va_O1_2"]
        defects = []
        for dd in defect_dirs:
            file = os.path.join(test_dir, "MgO", "defects", dd, "defect.json")
            defects.append(Defect.load_json(file))

        # temporary insert values
        chem_pot = ChemPotDiag.load_vertices_yaml(
            os.path.join(test_dir, "MgO/vertices_MgO.yaml"))

        chem_pot_label = "A"

        self.defect_energies = \
            DefectEnergies.from_objects(unitcell=unitcell,
                                        perfect=perfect,
                                        defects=defects,
                                        chem_pot=chem_pot,
                                        chem_pot_label=chem_pot_label,
                                        system="MgO")

    def test_print(self):
        print(self.defect_energies)

    def test_energies(self):
        d = self.defect_energies.as_dict()
        de = DefectEnergies.from_dict(d)
        dd = de.as_dict()
        self.assertEqual(d, dd)
        print(d)
        print(dd)

    def test_json(self):
        """ round trip test of to_json and from_json """
        tmp_file = tempfile.NamedTemporaryFile()
        self.defect_energies.to_json_file(tmp_file.name)
        defect_entry_from_json = DefectEntry.load_json(tmp_file.name)
        print(defect_entry_from_json.as_dict())
        print(self.defect_energies.as_dict())
        self.assertEqual(defect_entry_from_json.as_dict(),
                         self.defect_energies.as_dict())

    # def test_multiplicity(self):
    #     actual = self.energies.multiplicity["Va_O1"][2][0]
    #     expected = 8
    #     self.assertEqual(actual, expected)

    def test_U(self):
        actual = self.defect_energies.u(name="Va_O1", charges=[0, 1, 2])[0]
        expected = 1.82926181856907
        self.assertAlmostEqual(actual, expected)

    def test_calc_transition_levels(self):
        dp = self.defect_energies
#        dp = DefectEnergyPlotter(self.energies, self.dc2)
#        plt = dp.plot_energy(filtering_words=["Va_O[0-9]+"],
        plt = dp.plot_energy(x_range=[-0.15, 4.5],
                             fermi_levels=[[1000, 4.5], [298, 3.3]],
                             show_transition_levels=True,
                             show_all_energies=True)
        plt.show()
#        plt.savefig(fname="energy.eps")


if __name__ == "__main__":
    unittest.main()

