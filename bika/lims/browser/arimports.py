# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

import csv
import json
from DateTime.DateTime import DateTime
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims import logger
from bika.lims.browser import BrowserView, ulocalized_time
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.content.arimport import get_row_container
from bika.lims.content.arimport import get_row_profile_services
from bika.lims.content.arimport import get_row_services
from bika.lims.content.arimport import convert_date_string
from bika.lims.content.arimport import lookup_sampler_uid
from bika.lims.idserver import renameAfterCreation
from bika.lims.interfaces import IClient
from bika.lims.utils import tmpID
from bika.lims.workflow import getTransitionDate
from plone import api as ploneapi
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.layout.globals.interfaces import IViewView
from plone.protect import CheckAuthenticator
from Products.Archetypes.utils import addStatusMessage
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import _createObjectByType
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.interface import alsoProvides
from zope.interface import implements

from zope import event

import os


class ARImportsView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(ARImportsView, self).__init__(context, request)
        request.set('disable_plone.rightcolumn', 1)
        alsoProvides(request, IContentListing)

        self.catalog = "portal_catalog"
        self.contentFilter = {
            'portal_type': 'ARImport',
            'cancellation_state': 'active',
            'sort_on': 'sortable_title',
        }
        self.context_actions = {}
        if IClient.providedBy(self.context):
            self.context_actions = {
                _('AR Import'): {
                    'url': 'arimport_add',
                    'icon': '++resource++bika.lims.images/add.png'}}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = False
        self.pagesize = 50
        self.form_id = "arimports"

        self.icon = \
            self.portal_url + "/++resource++bika.lims.images/arimport_big.png"
        self.title = self.context.translate(_("Analysis Request Imports"))
        self.description = ""

        self.columns = {
            'Title': {'title': _('Title')},
            'Client': {'title': _('Client')},
            'Filename': {'title': _('Filename')},
            'Creator': {'title': _('Date Created')},
            'DateCreated': {'title': _('Date Created')},
            'DateValidated': {'title': _('Date Validated')},
            'DateImported': {'title': _('Date Imported')},
            'state_title': {'title': _('State')},
        }
        self.review_states = [
            {'id': 'default',
             'title': _('Pending'),
             'contentFilter': {'review_state': ['invalid', 'valid']},
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'Client',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
            {'id': 'imported',
             'title': _('Imported'),
             'contentFilter': {'review_state': 'imported'},
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'Client',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
            {'id': 'cancelled',
             'title': _('Cancelled'),
             'contentFilter': {
                 'review_state': ['initial', 'invalid', 'valid', 'imported'],
                 'cancellation_state': 'cancelled'
             },
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'Client',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
        ]

    def folderitems(self, **kwargs):
        items = super(ARImportsView, self).folderitems()
        for x in range(len(items)):
            if 'obj' not in items[x]:
                continue
            obj = items[x]['obj']
            items[x]['Title'] = obj.title_or_id()
            if items[x]['review_state'] == 'invalid':
                items[x]['replace']['Title'] = "<a href='%s/edit'>%s</a>" % (
                    obj.absolute_url(), items[x]['Title'])
            else:
                items[x]['replace']['Title'] = "<a href='%s/view'>%s</a>" % (
                    obj.absolute_url(), items[x]['Title'])
            items[x]['Creator'] = obj.Creator()
            items[x]['Filename'] = obj.getFilename()
            parent = obj.aq_parent
            items[x]['Client'] = parent if IClient.providedBy(parent) else ''
            items[x]['replace']['Client'] = "<a href='%s'>%s</a>" % (
                parent.absolute_url(), parent.Title())
            items[x]['DateCreated'] = ulocalized_time(
                obj.created(), long_format=True, time_only=False, context=obj)
            date = getTransitionDate(obj, 'validate')
            items[x]['DateValidated'] = date if date else ''
            date = getTransitionDate(obj, 'import')
            items[x]['DateImported'] = date if date else ''

        return items


class ClientARImportsView(ARImportsView):
    def __init__(self, context, request):
        super(ClientARImportsView, self).__init__(context, request)
        self.contentFilter['path'] = {
            'query': '/'.join(context.getPhysicalPath())
        }

        self.review_states = [
            {'id': 'default',
             'title': _('Pending'),
             'contentFilter': {'review_state': ['invalid', 'valid']},
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
            {'id': 'imported',
             'title': _('Imported'),
             'contentFilter': {'review_state': 'imported'},
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
            {'id': 'cancelled',
             'title': _('Cancelled'),
             'contentFilter': {
                 'review_state': ['initial', 'invalid', 'valid', 'imported'],
                 'cancellation_state': 'cancelled'
             },
             'columns': ['Title',
                         'Creator',
                         'Filename',
                         'DateCreated',
                         'DateValidated',
                         'DateImported',
                         'state_title']},
        ]


class ClientARImportAddView(BrowserView):
    implements(IViewView)
    template = ViewPageTemplateFile('templates/arimport_add.pt')

    def __init__(self, context, request):
        super(ClientARImportAddView, self).__init__(context, request)
        alsoProvides(request, IContentListing)

    def __call__(self):
        request = self.request
        form = request.form
        CheckAuthenticator(form)
        if form.get('submitted'):
            # Validate form submission
            csvfile = form.get('csvfile')
            data = csvfile.read()
            lines = data.splitlines()
            filename = csvfile.filename
            if not csvfile:
                addStatusMessage(request, _("No file selected"))
                return self.template()
            if len(lines) < 3:
                addStatusMessage(request, _("Too few lines in CSV file"))
                return self.template()
            # Create the arimport object
            arimport = _createObjectByType("ARImport", self.context, tmpID())
            arimport.processForm()
            arimport.setTitle(self.mkTitle(filename))
            arimport.schema['OriginalFile'].set(arimport, data)
            # Save all fields from the file into the arimport schema
            arimport.save_header_data()
            arimport.save_sample_data()
            # immediate batch creation if required
            arimport.create_or_reference_batch()
            # Attempt first validation
            try:
                workflow = getToolByName(self.context, 'portal_workflow')
                workflow.doActionFor(arimport, 'validate')
            except WorkflowException:
                self.request.response.redirect(arimport.absolute_url() +
                                               "/edit")
        else:
            return self.template()

    def mkTitle(self, filename):
        pc = getToolByName(self.context, 'portal_catalog')
        nr = 1
        while True:
            newname = '%s-%s' % (os.path.splitext(filename)[0], nr)
            existing = pc(portal_type='ARImport', title=newname)
            if not existing:
                return newname
            nr += 1


class ARImportAsyncView(BrowserView):

    def __call__(self):

        form = self.request.form
        gridrows = json.loads(form.get('gridrows', '[]'))
        client_uid = form.get('client_uid', None)
        if client_uid is None:
            raise RuntimeError('ARImportAsyncView: client is required')
        client = ploneapi.content.get(UID=client_uid)
        batch = None
        batch_uid = form.get('batch_uid', None)
        if batch_uid is not None:
            batch = ploneapi.content.get(UID=batch_uid)
        client_ref = form.get('client_ref', None)
        client_order_num = form.get('client_order_num', None)
        contact = None
        contact_uid = form.get('contact_uid', None)
        if contact_uid is not None:
            contact = ploneapi.content.get(UID=contact_uid)

        workflow = ploneapi.portal.get_tool('portal_workflow')
        bsc = ploneapi.portal.get_tool('bika_setup_catalog')
        profiles = [x.getObject() for x in bsc(
            portal_type='AnalysisProfile',
            inactive_state='active')]

        ar_list = []
        error_list = []
        row_cnt = 0
        for therow in gridrows:
            row = therow.copy()
            row_cnt += 1
            # Create Sample
            sample = _createObjectByType('Sample', client, tmpID())
            sample.unmarkCreationFlag()
            # First convert all row values into something the field can take
            sample.edit(**row)
            sample._renameAfterCreation()
            event.notify(ObjectInitializedEvent(sample))
            sample.at_post_create_script()
            bika_setup = api.get_bika_setup()
            swe = bika_setup.getSamplingWorkflowEnabled()
            if swe:
                workflow.doActionFor(sample, 'sampling_workflow')
            else:
                workflow.doActionFor(sample, 'no_sampling_workflow')
            part = _createObjectByType('SamplePartition', sample, 'part-1')
            part.unmarkCreationFlag()
            renameAfterCreation(part)
            if swe:
                workflow.doActionFor(part, 'sampling_workflow')
            else:
                workflow.doActionFor(part, 'no_sampling_workflow')
            # Container is special... it could be a containertype.
            container = get_row_container(row)
            if container:
                if container.portal_type == 'ContainerType':
                    containers = container.getContainers()
                # XXX And so we must calculate the best container for this partition
                part.edit(Container=containers[0])

            # Profiles are titles, profile keys, or UIDS: convert them to UIDs.
            newprofiles = []
            for title in row['Profiles']:
                objects = []
                for x in profiles:
                    if title in (x.getProfileKey(), x.UID(), x.Title()):
                        objects.append(x)
                for obj in objects:
                    newprofiles.append(obj.UID())
            row['Profiles'] = newprofiles

            # BBB in bika.lims < 3.1.9, only one profile is permitted
            # on an AR.  The services are all added, but only first selected
            # profile name is stored.
            row['Profile'] = newprofiles[0] if newprofiles else None

            # Same for analyses
            (analyses, errors) = get_row_services(row)
            if errors:
                for err in errors:
                    error_list(err)
            newanalyses = set(analyses)
            (analyses, errors) = get_row_profile_services(row)
            if errors:
                for err in errors:
                    error_list(err)
            newanalyses.update(analyses)
            row['Analyses'] = []
            # get batch
            if batch is not None:
                row['Batch'] = batch
            # Add AR fields from schema into this row's data
            if client_ref:
                row['ClientReference'] = client_ref
            if client_order_num:
                row['ClientOrderNumber'] = client_order_num
            if contact:
                row['Contact'] = contact
            row['DateSampled'] = convert_date_string(row['DateSampled'])
            if row['Sampler']:
                row['Sampler'] = lookup_sampler_uid(row['Sampler'])

            # Create AR
            ar = _createObjectByType("AnalysisRequest", client, tmpID())
            ar.setSample(sample)
            ar.unmarkCreationFlag()
            ar.edit(**row)
            ar._renameAfterCreation()
            ar.setAnalyses(list(newanalyses))
            for analysis in ar.getAnalyses(full_objects=True):
                analysis.setSamplePartition(part)
            ar.at_post_create_script()
            if swe:
                workflow.doActionFor(ar, 'sampling_workflow')
            else:
                workflow.doActionFor(ar, 'no_sampling_workflow')
            ar_list.append(ar.getId())
            logger.info('Created AR %s' % ar.getId())
        logger.info('AR Import Complete')

        # Email user
        mail_template = """
Dear {name},

Analysis requests import complete
{ars_msg}
{error_msg}

Cheers
Bika LIMS
"""
        mail_host = ploneapi.portal.get_tool(name='MailHost')
        from_email = mail_host.email_from_address
        member = ploneapi.user.get_current()
        to_email = member.getProperty('email')
        subject = 'AR Import Complete'
        name = member.getProperty('fullname')
        if len(to_email) == 0:
            to_email = from_email
            name = 'Sys Admin'
            subject = 'AR Import by admin user is complete'
        error_msg = ''
        if len(error_list):
            error_msg = 'Errors:\n' + '\n'.join(error_list)

        mail_text = mail_template.format(
                        name=name,
                        ars_msg='\n'.join(ar_list),
                        error_msg=error_msg)
        try:
            mail_host.send(
                        mail_text, to_email, from_email,
                        subject=subject, charset="utf-8", immediate=False)
        except smtplib.SMTPRecipientsRefused:
            raise smtplib.SMTPRecipientsRefused(
                        'Recipient address rejected by server')
        logger.info('AR Import Completion emailed to %s' % to_email)
