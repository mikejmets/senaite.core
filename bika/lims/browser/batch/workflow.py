# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims.browser.analysisrequest.workflow import AnalysisRequestWorkflowAction


class BatchWorkflowAction(AnalysisRequestWorkflowAction):
    """Button Action Handler for Batches
    """

    def workflow_action_invoice_batch(self):
        """Invoke the ar_add form in the current context, passing the UIDs of
        the source ARs as request parameters.
        """
        objects = BatchWorkflowAction._get_selected_items(self)
        context = self.context
        if not objects:
            message = context.translate(
                _("No analyses have been selected"))
            self.context.plone_utils.addPortalMessage(message, 'info')
            self.destination_url = self.context.absolute_url() + \
                                   "/batchbook"
            self.request.response.redirect(self.destination_url)
            return

        #Validate client
        if context.portal_type == 'AnalysisRequestsFolder':
            clients = [objects[cln].aq_parent.Title() for cln in objects.keys()]
            for c in clients:
                if clients[0] != c:
                    message = context.translate(
                        _("Multiple Clients selected"))
                    self.context.plone_utils.addPortalMessage(message, 'error')
                    self.destination_url = self.context.absolute_url()
                    self.request.response.redirect(self.destination_url)
                    return
            client = objects[objects.keys()[0]]

        elif context.portal_type == 'Batch':
            client = context.getClient()

        elif context.portal_type == 'Client':
            client = context

        url = '{}/batchinvoice?items={}'.format(
                self.context.absolute_url(),
                ','.join(objects.keys()))
        print url
        self.request.response.redirect(url)
        return
