import numpy as np

from spikeinterface.core import NumpySorting
from spikeinterface.curation import CurationSorting, MergeUnitsSorting, SplitUnitSorting


def test_split_merge():
    spikestimes = [
        {
            0: np.arange(15),
            1: np.arange(17),
            2: np.arange(17) + 5,
            4: np.concatenate([np.arange(10), np.arange(20, 30)]),
            5: np.arange(9),
        },
        {0: np.arange(15), 1: np.arange(17), 2: np.arange(40, 140), 4: np.arange(40, 140), 5: np.arange(40, 140)},
    ]
    parent_sort = NumpySorting.from_unit_dict(spikestimes, sampling_frequency=1000)  # to have 1 sample=1ms
    parent_sort.set_property("someprop", [float(k) for k in spikestimes[0].keys()])  # float

    split_index = [v[4] % 2 for v in spikestimes]  # spit class 4 in even and odds
    splitted = SplitUnitSorting(
        parent_sort, split_unit_id=4, indices_list=split_index, new_unit_ids=[8, 10], properties_policy="keep"
    )
    # add array property (with same values for units to be merged) -> keep
    some_array_prop_same_values = np.ones((len(splitted.unit_ids), 2))
    splitted.set_property("some_array_prop_to_keep", some_array_prop_same_values)
    # add float array property (with different values for units to be merged) -> nan
    some_array_prop_to_remove = np.random.randn(len(splitted.unit_ids), 2)
    splitted.set_property("some_array_prop_to_remove", some_array_prop_to_remove)
    # add str property (with different values for units to be merged) -> ""
    some_str_prop = ["merge"] * len(splitted.unit_ids)
    some_str_prop[-1] = "different"
    splitted.set_property("some_str_prop", some_str_prop)
    # add int array property (with different values for units to be merged) -> None
    some_array_prop_to_set_none = np.ones((len(splitted.unit_ids), 2), dtype=int)
    some_array_prop_to_set_none[-1] = [1, 2]
    splitted.set_property("some_array_prop_to_set_none", some_array_prop_to_set_none)

    merged = MergeUnitsSorting(splitted, units_to_merge=[[8, 10]], new_unit_ids=[4], properties_policy="keep")
    for i in range(len(spikestimes)):
        assert (
            all(parent_sort.get_unit_spike_train(4, segment_index=i) == merged.get_unit_spike_train(4, segment_index=i))
            == True
        ), "splir or merge error"
    assert parent_sort.get_unit_property(4, "someprop") == merged.get_unit_property(
        4, "someprop"
    ), "property wasn't kept"
    assert np.array_equal(merged.get_unit_property(4, "some_array_prop_to_keep"), [1, 1]), "error with array property"
    assert np.all(np.isnan(merged.get_unit_property(4, "some_array_prop_to_remove"))), "error with array property"
    assert np.array_equal(
        merged.get_unit_property(4, "some_array_prop_to_set_none"), [None, None]
    ), "error with array property"
    assert merged.get_unit_property(4, "some_str_prop") == "", "error with array property"

    merged_with_dups = MergeUnitsSorting(
        parent_sort, new_unit_ids=[8], units_to_merge=[[0, 1]], properties_policy="remove", delta_time_ms=0.5
    )
    for i in range(len(spikestimes)):
        assert all(
            merged_with_dups.get_unit_spike_train(8, segment_index=i)
            == parent_sort.get_unit_spike_train(1, segment_index=i)
        ), "error removing duplications"
    assert np.isnan(merged_with_dups.get_unit_property(8, "someprop")), "error creating empty property"


def test_curation():
    spikestimes = [
        {
            "a": np.arange(15),
            "b": np.arange(5, 10),
            "c": np.arange(20),
        },
        {"a": np.arange(12, 15), "b": np.arange(3, 17), "c": np.arange(50)},
    ]
    parent_sort = NumpySorting.from_unit_dict(spikestimes, sampling_frequency=1000)  # to have 1 sample=1ms
    parent_sort.set_property("some_names", ["unit_{}".format(k) for k in spikestimes[0].keys()])  # float
    cs = CurationSorting(parent_sort, properties_policy="remove")
    cs.merge(["a", "c"])
    assert cs.sorting.get_num_units() == len(spikestimes[0]) - 1
    split_index = [v["b"] < 6 for v in spikestimes]  # split class 4 in even and odds
    cs.split("b", split_index)
    after_split = cs.sorting
    assert cs.sorting.get_num_units() == len(spikestimes[0])

    all_units = cs.sorting.get_unit_ids()
    cs.merge(all_units, new_unit_id=all_units[0])
    assert len(cs.sorting.get_unit_ids()) == 1, "error merging units"
    assert cs.sorting.unit_ids[0] == all_units[0]
    cs.undo()

    assert cs.sorting is after_split
    cs.redo()
    unit = cs.sorting.get_unit_ids()[0]
    for i in range(len(spikestimes)):
        assert all(
            cs.sorting.get_unit_spike_train(unit, segment_index=i)
            == parent_sort.get_unit_spike_train("c", segment_index=i)
        )

    # Test with empty sorting
    empty_sorting = CurationSorting(NumpySorting.from_unit_dict({}, parent_sort.sampling_frequency))


if __name__ == "__main__":
    test_split_merge()
    test_curation()
