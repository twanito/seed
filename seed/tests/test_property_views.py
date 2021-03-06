# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from datetime import datetime
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    Column,
    Cycle,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory, FakeColumnFactory,
    FakePropertyFactory, FakePropertyStateFactory,
    FakeTaxLotStateFactory
)

COLUMNS_TO_SEND = [
    'project_id',
    'address_line_1',
    'city',
    'state_province',
    'postal_code',
    'pm_parent_property_id',
    'calculated_taxlot_ids',
    'primary',
    'extra_data_field',
    'jurisdiction_tax_lot_id'
]


class PropertyViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org = Organization.objects.create()
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory()
        self.taxlot_state_factory = FakeTaxLotStateFactory()
        self.org_user = OrganizationUser.objects.create(
            user=self.user, organization=self.org
        )
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))
        self.client.login(**user_details)

    def tearDown(self):
        Column.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        TaxLot.objects.all().delete()
        TaxLotProperty.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()
        Cycle.objects.all().delete()
        self.user.delete()
        self.org.delete()
        self.org_user.delete()

    def test_get_and_edit_properties(self):
        state = self.property_state_factory.get_property_state(self.org)
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }

        url = reverse('api:v2:properties-list') + '?cycle_id={}'.format(self.cycle.pk)
        response = self.client.get(url, params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(results['address_line_1'], state.address_line_1)

        db_created_time = results['db_property_created']
        db_updated_time = results['db_property_updated']
        self.assertTrue(db_created_time is not None)
        self.assertTrue(db_updated_time is not None)

        # update the address
        new_data = {
            "state": {
                "address_line_1": "742 Evergreen Terrace"
            }
        }
        url = reverse('api:v2:properties-detail', args=[prprty.id]) + \
            '?cycle_id={}&organization_id={}'.format(self.cycle.pk, self.org.pk)
        response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')

        # the above call returns data from the PropertyState, need to get the Property --
        # call the get on the same API to retrieve it
        response = self.client.get(url, content_type='application/json')
        result = json.loads(response.content)
        # make sure the address was updated and that the datetimes were modified
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['state']['address_line_1'], '742 Evergreen Terrace')
        self.assertEqual(datetime.strptime(db_created_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0),
                         datetime.strptime(result['property']['db_property_created'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                             microsecond=0))
        self.assertGreater(datetime.strptime(result['property']['db_property_updated'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                           datetime.strptime(db_updated_time, "%Y-%m-%dT%H:%M:%S.%fZ"))
