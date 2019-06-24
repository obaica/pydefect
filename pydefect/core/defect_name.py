# -*- coding: utf-8 -*-
import re
from typing import Union

from monty.json import MSONable

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"


class DefectName(MSONable):
    def __init__(self,
                 name: str,
                 charge: int,
                 annotation: str = None):

        self.name = name
        self.charge = charge
        self.annotation = annotation

    @property
    def name_str(self):
        return self.name

    def is_name_matched(self,
                        keywords: Union[str, list, None]):
        """ Return True if name is matched by the selected_keywords.

        Args:
            keywords (str/list): Keywords used for checking if name is selected.

        When the following type names are given, constructs a set of defects.
            "Va"    --> A set of all the vacancies.
            "_i"     --> A set of all the interstitials.
            "Va_O"  --> A set of all the oxygen vacancies
            "Va_O[0-9]_0" --> All the oxygen vacancies in neutral charge states
            "Va_O1" --> A set of oxygen vacancies at O1 site
            "Mg_O"  --> A set of all the Mg-on-O antisite pairs.
            "Mg_O1" --> A set of Mg-on-O1 antisite pairs.

        When complete defect_name is given, constructs a particular defect.
            e.g., "Va_O1_2",  "Mg_O1_0"
        """
        if keywords is None:
            return True

        try:
            if isinstance(keywords, str):
                keywords = [keywords]
            else:
                keywords = list(keywords)
        except TypeError:
            print("The type of keywords {} is invalid.".format(keywords))

        return any([re.search(p, self.__str__()) for p in keywords])

    def __str__(self):
        if self.annotation:
            return "_".join([self.name_str, str(self.charge), self.annotation])
        else:
            return "_".join([self.name_str, str(self.charge)])

    def __eq__(self, other):
        # Note: charge is not compared
        if isinstance(other, str):
            return True if self.__str__() == other else False
        elif isinstance(other, DefectName):
            return True if self.__str__() == other.__str__() else False
        else:
            raise TypeError(
                "{} is not supported for comparison.".format(type(other)))

    def __hash__(self):
        return hash(self.name_str)


class SimpleDefectName(DefectName):
    """ Container for a name of vacancy, interstitial, & antisite defect."""
    def __init__(self,
                 in_atom: Union[str, None],
                 out_site: str,
                 charge: int,
                 annotation: str = None):
        if not re.match(r"[a-xA-Z0-9]+$", out_site):
            raise ValueError("out_site {} is not valid.")

        self.in_atom = in_atom
        self.out_site = out_site
        super().__init__(self.name_str, charge, annotation)

    @property
    def name_str(self):
        if self.in_atom:
            return "_".join([self.in_atom, self.out_site])
        else:
            return "_".join(["Va", self.out_site])

    @property
    def is_interstitial(self):
        return re.match(r"^i[a-xA-Z0-9]+$", self.out_site)

    @property
    def is_vacancy(self):
        return True if self.in_atom is None else False

    @classmethod
    def from_str(cls, string):
        in_atom, out_site, charge = string.split("_")
        if in_atom == "Va":
            in_atom = None
        return cls(in_atom, out_site, int(charge))