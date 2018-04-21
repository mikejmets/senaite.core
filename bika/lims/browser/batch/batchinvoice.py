# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.browser import BrowserView
from bika.lims.utils import to_utf8
from bika.lims.permissions import *
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone.utils import _createObjectByType
from decimal import Decimal

import os
from bika.lims.utils import createPdf


class BatchInvoiceView(BrowserView):

    template = ViewPageTemplateFile("templates/batch_invoice.pt")
    pdf_template = ViewPageTemplateFile("templates/batch_pdf.pt")
    # content = ViewPageTemplateFile("templates/analysisrequest_invoice_content.pt")
    title = _('Batch Invoice')
    description = ''

    def __call__(self):
        # context = self.context
        self.rendered_items = []
        bc = getToolByName(self.context, 'bika_catalog')
        self.items = self.request.get('items', '')
        self.invoice_id = 'Proforma (Not yet invoiced)'
        if self.items:
            self.items = [o.getObject() for o in bc(UID=self.items.split(","))]
        else:
            # TODO: Get all ARs that have not been invoiced on this batch
            self.items = self.context.getAnalysisRequests()
        # self.create_invoice is True if there's no PDF
        # Also make if True if one of the ARs is not verified
        self.create_invoice = False
        self.downloadable = True if self.context.getPdf() else False
        if self.downloadable:
            # All the ARs have the same invoice id on this batch
            self.invoice_id = self.items[0].getInvoice().getId()
        if self.context.areAnalysisRequestsVerified() and self.downloadable == False:
            self.create_invoice = True

        return self.template()

    def issue_invoice(self):
        """Issue invoice
        """
        # Create PDF of invoice from the view
        self.downloadable = True if self.context.getPdf() else False
        if self.context.areAnalysisRequestsVerified() and self.downloadable == False:
            self.create_invoice = True

        # check for an adhoc invoice batch for this month
        # noinspection PyCallingNonCallable
        now = DateTime()
        batch_month = now.strftime('%b %Y')
        batch_title = '%s - %s' % (batch_month, 'ad hoc')
        invoice_batch = None
        for b_proxy in self.portal_catalog(portal_type='InvoiceBatch',
                                           Title=batch_title):
            invoice_batch = b_proxy.getObject()
        if not invoice_batch:
            # noinspection PyCallingNonCallable
            first_day = DateTime(now.year(), now.month(), 1)
            start_of_month = first_day.earliestTime()
            last_day = first_day + 31
            # noinspection PyUnresolvedReferences
            while last_day.month() != now.month():
                last_day -= 1
            # noinspection PyUnresolvedReferences
            end_of_month = last_day.latestTime()

            invoices = self.context.invoices
            batch_id = invoices.generateUniqueId('InvoiceBatch')
            invoice_batch = _createObjectByType("InvoiceBatch", invoices,
                                                batch_id)
            invoice_batch.edit(
                title=batch_title,
                BatchStartDate=start_of_month,
                BatchEndDate=end_of_month,
            )
            invoice_batch.processForm()

        client_uid = self.context.getClientUID()
        # client_title = self.context.getClientTitle()
        # Get the created invoice
        # TODO: check invoiced for ARs that are not invoice
        ars = self.context.getAnalysisRequests()
        invoice = invoice_batch.createInvoice(client_uid, ars)
        invoice.setAnalysisRequest(self)
        self.invoice_id = invoice.getId()
        # Set the created invoice in the schema
        for ar in ars:
            ar.setInvoice(invoice)
        invoice_pdf = self.pdf_template()
        # content = ''
        this_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(this_dir, 'templates/')
        css = '%s%s.css' % (templates_dir, 'batch_pdf')
        pdf_report = createPdf(invoice_pdf, False, css)
        self.context.setPdf(pdf_report)
        self.context.getPdf().setContentType('application/pdf')
        self.context.getPdf().setFilename("{}.pdf".format(self.invoice_id))
        redirect_url = '{}/batchinvoice'.format(self.context.absolute_url())
        self.request.response.redirect(redirect_url)
        return

    def format_address(self, address):
        if address:
            _keys = ['address', 'city', 'district', 'state', 'zip', 'country']
            _list = ["<div>%s</div>" % address.get(v) for v in _keys
                     if address.get(v)]
            return ''.join(_list)
        return ''

    def _client_address(self, client):
        client_address = client.getPostalAddress()
        if not client_address:
            ar = self.getAnalysisRequestObj()
            if not IAnalysisRequest.providedBy(ar):
                return ""
            # Data from the first contact
            contact = ar.getContact()
            if contact and contact.getBillingAddress():
                client_address = contact.getBillingAddress()
            elif contact and contact.getPhysicalAddress():
                client_address = contact.getPhysicalAddress()
        return self.format_address(client_address)

    def client_data(self):
        data = {}
        client = self.context.getClient()
        if client:
            data['obj'] = client
            data['id'] = client.id
            data['url'] = client.absolute_url()
            data['name'] = to_utf8(client.getName())
            data['phone'] = to_utf8(client.getPhone())
            data['vat'] = to_utf8(client.getTaxNumber())
            data['email'] = to_utf8(client.getEmailAddress())
            data['fax'] = to_utf8(client.getFax())

            data['address'] = to_utf8(self._client_address(client))
        return data

    def _lab_address(self, lab):
        lab_address = lab.getPostalAddress() \
                      or lab.getBillingAddress() \
                      or lab.getPhysicalAddress()
        return self.format_address(lab_address)

    def lab_data(self):
        portal = self.context.portal_url.getPortalObject()
        lab = self.context.bika_setup.laboratory

        return {'obj': lab,
                'title': to_utf8(lab.Title()),
                'url': to_utf8(lab.getLabURL()),
                'name': to_utf8(lab.getName()),
                'address': to_utf8(self._lab_address(lab)),
                'phone': to_utf8(lab.getPhone()),
                'vat': to_utf8(lab.getTaxNumber()),
                'email': to_utf8(lab.getEmailAddress()),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url(),
                'bank_account_holder': lab.getAccountName(),
                'bank_name': lab.getBankName(),
                'bank_branch': lab.getBankBranch(),
                'bank_account_number': lab.getAccountNumber(),
                }

    def getReportStyle(self):
        """ Returns the css style to be used for the current template.
            If the selected template is 'default.pt', this method will
            return the content from 'default.css'. If no css file found
            for the current template, returns empty string
        """
        # template = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        content = ''
        this_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(this_dir, 'templates/')
        path = '%s%s.css' % (templates_dir, 'batch_invoice')
        with open(path, 'r') as content_file:
            content = content_file.read()
        return content

    def totals(self):
        ars = self.ars_data()
        subtotal = 0
        subtotal_vat_amount = 0
        subtotal_total_price = 0
        discount = 0
        vat_amount = 0
        total_price = 0
        discounted_subtotal = 0
        discount_percentage = 0
        for ar in ars:
            # Without discount
            subtotal += float(ar['subtotal'])
            subtotal_vat_amount += float(ar['subtotal_vat_amount'])
            subtotal_total_price += float(ar['subtotal_total_price'])
            # With discount
            discount += float(ar['discount'])
            discounted_subtotal += float(ar['discounted_subtotal'])
            vat_amount += float(ar['vat_amount'])
            total_price += float(ar['total_price'])
            discount_percentage = float(ar['discount_percentage'])

        return {'subtotal': subtotal,  # Without Discount and VAT
                'discount_percentage': discount_percentage,
                'discount': discount,
                'discounted_subtotal': discounted_subtotal,
                'vat_amount': vat_amount,  # VAT from Discount
                'total_price': total_price,  # With Discount and VAT
                }

    def ars_data(self):
        ars = []
        self.items = self.context.getAnalysisRequests()
        for item in self.items:
            ar = self.ar_data(item)
            # if not ar['invoiced']:
            ars.append(ar)
        return ars

    def ar_data(self, ar):
        analyses = []
        profiles = []
        # Retrieve required data from analyses collection
        all_analyses, all_profiles, analyses_from_profiles = ar.getServicesAndProfiles()
        # Relating category with solo analysis
        for analysis in all_analyses:
            service = analysis.getService()
            categoryName = service.getCategory().Title()
            # Find the category
            try:
                category = (
                    o for o in analyses if o['name'] == categoryName
                ).next()
            except:
                category = {'name': categoryName, 'analyses': []}
                analyses.append(category)
            # Append the analysis to the category
            category['analyses'].append({
                'title': analysis.Title(),
                'price': analysis.getPrice(),
                'priceVat': "%.2f" % analysis.getVATAmount(),
                'priceTotal': "%.2f" % analysis.getTotalPrice(),
            })
        # Relating analysis services with their profiles
        # We'll take the analysis contained on each profile
        for profile in all_profiles:
            # If profile's checkbox "Use Analysis Profile Price" is enabled, only the profile price will be displayed.
            # Otherwise each analysis will display its own price.
            pservices = []
            if profile.getUseAnalysisProfilePrice():
                # We have to use the profiles price only
                for pservice in profile.getService():
                    pservices.append({'title': pservice.Title(),
                                      'price': None,
                                      'priceVat': None,
                                      'priceTotal': None,
                                      })
                profiles.append({'name': profile.title,
                                 'price': profile.getAnalysisProfilePrice(),
                                 'priceVat': profile.getVATAmount(),
                                 'priceTotal': profile.getTotalPrice(),
                                 'analyses': pservices})
            else:
                # We need the analyses prices instead of profile price
                for pservice in profile.getService():
                    # We want the analysis instead of the service, because we want the price for the client
                    # (for instance the bulk price)
                    panalysis = self._getAnalysisForProfileService(pservice.getKeyword(), analyses_from_profiles)
                    if panalysis == 0:
                        continue
                    else:
                        pservices.append({'title': pservice.Title(),
                                          'price': panalysis.getPrice(),
                                          'priceVat': "%.2f" % panalysis.getVATAmount(),
                                          'priceTotal': "%.2f" % panalysis.getTotalPrice(),
                                          })
                profiles.append({'name': profile.title,
                                 'price': None,
                                 'priceVat': None,
                                 'priceTotal': None,
                                 'analyses': pservices})
        self.analyses = analyses
        self.profiles = profiles
        # Get subtotals
        self.subtotal = ar.getSubtotal()
        self.subtotalVATAmount = "%.2f" % ar.getSubtotalVATAmount()
        self.subtotalTotalPrice = "%.2f" % ar.getSubtotalTotalPrice()
        # Get totals
        self.memberDiscount = Decimal(ar.getDefaultMemberDiscount())
        self.discountAmount = ar.getDiscountAmount()
        self.VATAmount = "%.2f" % ar.getVATAmount()
        self.totalPrice = "%.2f" % ar.getTotalPrice()
        self.discounted_subtotal = self.subtotal - self.discountAmount
        # TODO: Check if an ar has been invoiced
        invoiced = False
        if ar.getInvoice():
            invoiced = True

        sample = ar.getSample()
        samplePoint = sample.getSamplePoint().Title() if sample.getSamplePoint() else ''
        sampleType = sample.getSampleType().Title()
        date_received = self.ulocalized_time(ar.getDateReceived(), long_format=1)
        if not date_received:
            date_received = 'Proforma'
        date_published = self.ulocalized_time(ar.getDatePublished(), long_format=1)
        if not date_published:
            date_published = 'Proforma'
        adict = {'sample': sample.Title(),
                 'ar': ar.id,
                 'sample_type': sampleType,
                 'sample_point': samplePoint,
                 'profile': '',  # TODO: profile
                 'date_received': date_received,
                 'date_published': date_published,

                 'subtotal': self.subtotal,
                 'subtotal_vat_amount': self.subtotalVATAmount,
                 'subtotal_total_price': self.subtotalTotalPrice,

                 'discount_percentage': self.memberDiscount,
                 'discount': self.discountAmount,
                 'vat_amount': self.VATAmount,
                 'discounted_subtotal': self.discounted_subtotal,
                 'total_price': self.totalPrice,

                 'state': api.get_workflow_status_of(ar),
                 'invoiced': invoiced,
                 }
        return adict
