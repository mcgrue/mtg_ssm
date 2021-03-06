"""Tests for mtg_ssm.serialization.interface.py"""

import unittest

from mtg_ssm.mtg import collection
from mtg_ssm.mtg import models
from mtg_ssm.serialization import interface

from tests.mtgjson import mtgjson_testcase


class StubSerializer(interface.MtgSsmSerializer):
    """Stub serializer for testing purposes."""

    format = None
    extension = None
    write_to_file = None
    read_from_file = None


class SubclassRegistrationTest(unittest.TestCase):

    def test_all_formats(self):
        all_formats = interface.MtgSsmSerializer.all_formats()
        expected = ['auto', 'csv', 'xlsx', 'deckbox']
        self.assertCountEqual(expected, all_formats)
        self.assertEqual('auto', expected[0])

    def test_auto_csv(self):
        serializer_class = interface.MtgSsmSerializer.by_extension_and_format(
            '.csv', 'auto')
        self.assertIsInstance(serializer_class, type)
        self.assertEqual('MtgCsvSerializer', serializer_class.__name__)

    def test_manual_csv(self):
        serializer_class = interface.MtgSsmSerializer.by_extension_and_format(
            None, 'csv')
        self.assertIsInstance(serializer_class, type)
        self.assertEqual('MtgCsvSerializer', serializer_class.__name__)

    def test_auto_xlsx(self):
        serializer_class = interface.MtgSsmSerializer.by_extension_and_format(
            '.xlsx', 'auto')
        self.assertIsInstance(serializer_class, type)
        self.assertEqual('MtgXlsxSerializer', serializer_class.__name__)

    def test_manual_xlsx(self):
        serializer_class = interface.MtgSsmSerializer.by_extension_and_format(
            None, 'xlsx')
        self.assertIsInstance(serializer_class, type)
        self.assertEqual('MtgXlsxSerializer', serializer_class.__name__)

    def test_unknown_auto(self):
        with self.assertRaises(interface.InvalidExtensionOrFormat):
            interface.MtgSsmSerializer.by_extension_and_format('', 'auto')

    def test_unknown_format(self):
        with self.assertRaises(interface.InvalidExtensionOrFormat):
            interface.MtgSsmSerializer.by_extension_and_format(None, 'foo')


class LoadCountsTest(mtgjson_testcase.MtgJsonTestCase):

    def setUp(self):
        super().setUp()
        self.collection = collection.Collection(self.mtg_data)
        self.print_id = '958ae1416f8f6287115ccd7c5c61f2415a313546'
        self.printing = self.collection.id_to_printing[self.print_id]
        self.serializer = StubSerializer(self.collection)

    def test_coerce_counts(self):
        counts = {'id': 'a', 'multiverseid': '12', 'copies': '4', 'foils': '5'}
        coerced_counts = interface.coerce_counts(counts)
        expected = {'id': 'a', 'multiverseid': 12, 'copies': 4, 'foils': 5}
        self.assertEqual(expected, coerced_counts)

    def test_printing_not_found(self):
        counts = {}
        with self.assertRaises(interface.DeserializationError):
            self.serializer.load_counts(counts)

    def test_load_nothing(self):
        counts = {'id': self.print_id}
        self.serializer.load_counts(counts)
        self.assertFalse(self.printing.counts)

    def test_load_zeros(self):
        counts = {'id': self.print_id, 'copies': 0, 'foils': 0}
        self.serializer.load_counts(counts)
        self.assertFalse(self.printing.counts)

    def test_load_counts(self):
        counts = {'id': self.print_id, 'copies': 1, 'foils': 2}
        self.serializer.load_counts(counts)
        expected = {
            models.CountTypes.copies: 1,
            models.CountTypes.foils: 2,
        }
        self.assertEqual(expected, self.printing.counts)

    def test_load_with_find(self):
        counts = {'set': 'S00', 'name': 'Rhox', 'copies': 1}
        self.serializer.load_counts(counts)
        printing = self.collection.id_to_printing[
            '536d407161fa03eddee7da0e823c2042a8fa0262']
        self.assertEqual({models.CountTypes.copies: 1}, printing.counts)

    def test_increase_counts(self):
        self.printing.counts[models.CountTypes.copies] = 1
        self.printing.counts[models.CountTypes.foils] = 2
        counts = {'id': self.print_id, 'copies': 4, 'foils': '8'}
        self.serializer.load_counts(counts)
        expected = {
            models.CountTypes.copies: 5,
            models.CountTypes.foils: 10,
        }
        self.assertEqual(expected, self.printing.counts)


class FindPrintingTest(mtgjson_testcase.MtgJsonTestCase):

    def setUp(self):
        super().setUp()
        self.collection = collection.Collection(self.mtg_data)

    def test_not_found(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='foo', name='bar', set_number='baz',
            multiverseid='quux')
        # Verify
        self.assertIsNone(printing)

    def test_set_and_name(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='S00', name='Rhox', set_number='foo',
            multiverseid='bar')
        # Verify
        self.assertEqual(
            '536d407161fa03eddee7da0e823c2042a8fa0262', printing.id_)

    def test_set_and_name_dupes(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='ICE', name='Forest',
            set_number=None, multiverseid=None)
        # Verify
        self.assertIsNone(printing)

    def test_set_name_num(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='pMGD', name="Black Sun's Zenith",
            set_number='7', multiverseid='foo')
        # Verify
        self.assertEqual(
            '6c9ffa9ffd2cf7e6f85c6be1713ee0c546b9f8fc', printing.id_)

    def test_set_name_mv(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='LEA', name='Forest',
            set_number='foo', multiverseid=288)
        # Verify
        self.assertEqual(
            '5ede9781b0c5d157c28a15c3153a455d7d6180fa', printing.id_)

    def test_get_set_name_num_mv(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='ISD', name='Abattoir Ghoul',
            set_number='85', multiverseid=222911)
        # Verify
        self.assertEqual(
            '958ae1416f8f6287115ccd7c5c61f2415a313546', printing.id_)

    def test_bad_set_code(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='foo', name='Abattoir Ghoul',
            set_number='85', multiverseid=222911)
        # Verify
        self.assertIsNone(printing)

    def test_bad_name(self):
        # Execute
        printing = interface.find_printing(
            coll=self.collection, set_code='ISD', name='foo', set_number='85',
            multiverseid=222911)
        # Verify
        self.assertIsNone(printing)
