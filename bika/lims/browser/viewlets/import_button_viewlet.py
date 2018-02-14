from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone import api
from plone.app.layout.viewlets.common import ViewletBase


class ImportButtonViewlet(ViewletBase):
    index = ViewPageTemplateFile('templates/import_button_viewlet.pt')

    def changeStatus(self):
        workflow = api.portal.get_tool("portal_workflow")
        state = api.content.get_state(self.context)
        available_transions = workflow.getTransitionsFor(self.context)
        self.import_buttons = []
        contextURL = self.context.absolute_url()
        changeWorkFlow = 'content_status_modify?workflow_action='
        for state in available_transions:
            url = '%s/%s%s' % (contextURL, changeWorkFlow, state['id'])
            self.import_buttons.append({'state': state['name'], 'url': url})
        return self.import_buttons
