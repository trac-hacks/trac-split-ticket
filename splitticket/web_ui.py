from pkg_resources import resource_filename
from time import localtime, strftime

# ensure OrderedDict is available when running under Python < 2.7
try:
   from collections import OrderedDict
except ImportError:
   from ordereddict import OrderedDict

from genshi.filters import Transformer
from genshi.template.base import Template
from genshi.template.loader import TemplateLoader

import trac.core
from trac.ticket.model import Milestone, Component, Ticket
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script


class SplitTicketWebUI(trac.core.Component):
    
    trac.core.implements(ITemplateProvider, IRequestFilter, ITemplateStreamFilter)

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        return [('splitticket', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if req.path_info.startswith('/ticket'):
            ticket = data['ticket']

            # add custom fields to the ticket template context data
            data['milestones'] = self._sorted_milestones()
            data['components'] = [c.name for c in Component.select(self.env)]
            data['split_options'] = self._ticket_split_options(ticket)
            data['split_history'] = self._ticket_split_history(ticket)

        return template, data, content_type

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename,  stream, data):
        if req.path_info.startswith('/ticket'):
            # add 'split' form markup to the ticket template event stream
            add_stylesheet(req, 'splitticket/css/split_controls.css')
            add_script(req, 'splitticket/js/jquery-1.7.2.min.js')
            add_script(req, 'splitticket/js/split_controls.js')

            markup = self._load_template_snippet('split_controls.html',
                                                 data=data)
            stream |= Transformer(".//label[@for='action_split']").after(markup)
    
            # add 'split history' markup to the ticket template event stream
            add_stylesheet(req, 'splitticket/css/split_history.css')
           
            markup = self._load_template_snippet('split_history.html',
                                                 data=data)
            stream |= Transformer(".//div[@id='ticket']").after(markup)
            
        return stream

    # Internal methods

    def _sorted_milestones(self):
        """ Return a sorted list of active milestones. """
        milestones = Milestone.select(self.env, include_completed=False)
        return [m.name for m in milestones]

    def _ticket_split_options(self, ticket):
        """ Return a collection of tickets which a given ticket may be split to.
        The tickets are sorted by milestone, component and then ticket ID. The 
        returned structure has the following form:

        { milestone: { component: [ticket, ...], ... }, ... }

        """
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        milestones = self._sorted_milestones()
        
        # get all active tickets (open and assigned to a milestone)
        cursor.execute("SELECT * FROM ticket WHERE milestone IN %s "
                       "AND status != %s AND id != %s "
                       "ORDER BY component, id",
                       (tuple(milestones), 'closed', ticket.id,))

        tickets = []
        for result in cursor.fetchall():
            ticket_id = result[0]
            ticket = Ticket(self.env, ticket_id)
            tickets.append(ticket)

        # sort tickets by milestone
        tickets.sort(key=lambda t: milestones.index(t['milestone']))
       
        # build up a sorted map of milestone > component > ticket
        split_options = OrderedDict()
       
        for ticket in tickets:
            milestone = ticket['milestone']
            component = ticket['component']

            if milestone not in split_options:
                split_options[milestone] = OrderedDict()

            if component not in split_options[milestone]:
                split_options[milestone][component] = [] 

            split_options[milestone][component].append(ticket)
            
        return split_options

    def _ticket_split_history(self, ticket):
        """ Return the split history for a given ticket. This is represented
        as a dictionary with the following structure:

        {
            'from': [{'source': <ticket id>, 'time': <split time>}, ...],
            'to': [{'target': <ticket id>, 'time': <split_time>}, ...]
        }
        
        """
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        split_history = {'from': [], 'to': []}

        # get any tickets that the current ticket was split from
        cursor.execute("SELECT * FROM ticket_split WHERE split_to = %s",
                       (ticket.id,))

        for split_from, _, split_time in cursor.fetchall():
            split = {}
            split['source'] = Ticket(self.env, split_from)
            split['time'] = strftime('%Y/%m/%d - %H:%M:%S', 
                                     localtime(split_time))
           
            split_history['from'].append(split)

        # get any tickets that the current ticket was split to
        cursor.execute("SELECT * FROM ticket_split WHERE ticket = %s "
                       "ORDER BY split_to", (ticket.id,))

        for _, split_target, split_time in cursor.fetchall():
            split = {}
            split['target'] = Ticket(self.env, split_target)
            split['time'] = strftime('%Y/%m/%d - %H:%M:%S', 
                                     localtime(split_time))
            
            split_history['to'].append(split)

        return split_history

    def _load_template_snippet(self, filename, data=None):
        """ Load a genshi template snippet from a file then apply the snippet
        to any supplied context data.

        :param filename: the name of the file containing the template snippet
        :param data: a dictionary of data to which the loaded template snippet
            may be applied

        The returned object is a Genshi Markup event stream, containing the
        HTML generated by applying the template snippet to any supplied context
        data.

        """
        loader = TemplateLoader(search_path=resource_filename(__name__, 'templates'))
        template = loader.load(filename)
        return template.generate(data=data)
