import re
import time

from trac.core import Component, implements
from trac.ticket.api import ITicketActionController
from trac.resource import ResourceNotFound
from trac.ticket.api import TicketSystem
from trac.ticket.model import Ticket


class SplitTicketWorkflow(Component):
    
    implements(ITicketActionController)

    # ITicketActionController methods

    def get_ticket_actions(self, req, ticket):
        return [(0, 'split')]

    def get_all_status(self):
        return set(['split']) 

    def render_ticket_action_control(self, req, ticket, action):
        return ('split ticket', None, None)

    def get_ticket_changes(self, req, ticket, action):
        return {}

    def apply_action_side_effects(self, req, ticket, action):
        stored_splits = self._stored_splits(ticket)
        latest_splits = self._latest_splits(req) 

        self._update_splits(ticket, stored_splits, latest_splits)

        split_count = self._update_splits(ticket, stored_splits, latest_splits)

        if split_count > 0:
            if ticket['status'] != 'split':
                # set status to split
                ticket['status'] = 'split'
                ticket.save_changes(author=req.authname, comment=None)
        else:
            if ticket['status'] == 'split':
                # ticket was split but splits have been deleted
                ticket['status'] = 'new'
                ticket.save_changes(author=req.authname, comment=None)

    # Internal methods

    def _stored_splits(self, ticket):
        """ Return a list of tickets split from a given ticket. """
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM ticket_split WHERE ticket = %s",
                       (ticket.id,))
        
        stored_splits = []
        for _, split_target, _ in cursor.fetchall():
            stored_splits.append(split_target)

        return stored_splits

    def _latest_splits(self, req):
        """ Return a list of tickets being split from a given ticket as part
        of an ongoing split action.

        N.B. This may involve the creation of new tickets required for the
        split. Where new tickets need to be created, the user will have
        specified a summary, milestone and component for each one using the
        'split' action interface provided by the plugin.
        
        :param req: the current trac request object (contains HTTP form data)

        """
        splits = []
        
        # process splits to existing tickets
        if 'field_split_existing' in req.args:
            for ticket_id in re.findall(r"\d+", req.args.get("field_split_existing")):
                # check ticket id is valid by attempting to retrieve the ticket
                try:
                    ticket = Ticket(self.env, ticket_id)
                    splits.append(int(ticket.id))
                except ResourceNotFound:
                    self.log.debug('Split to invalid ticket ID [%s] ignored' % ticket_id)

        # process splits to new tickets
        new_tickets = {}
       
        # grab all submitted information about new tickets from the request object
        regex = r'field_split_new_(?P<temp_ticket_id>\d+)_(?P<field_name>\w+)' 
        
        for field_name, value in req.args.items():
            match = re.match(regex, field_name)

            if match:
                temp_ticket_id = match.group('temp_ticket_id')
                field_name = match.group('field_name')
                field_value = value

                ticket = new_tickets.setdefault(temp_ticket_id, {})
                ticket[field_name] = field_value

        # create each new ticket required and add it's new ID to the list of splits
        for _, ticket_values in sorted(new_tickets.items()):
            ticket = Ticket(self.env)
            ticket['reporter'] = req.authname
            ticket['cc'] = ''
            ticket['version'] = ''
            ticket['keywords'] = ''
            ticket['description'] = ''
            ticket['summary'] = ticket_values['summary']
            ticket['milestone'] = ticket_values['milestone']
            ticket['component'] = ticket_values['component']
            ticket['status'] = 'new'
            ticket.insert()

            splits.append(int(ticket.id))

        return splits

    def _update_splits(self, ticket, stored, latest):
        """ Update the database to reflect any changes to splits involving a
        given ticket.

        :param stored: a list of the IDs of all tickets previously split from
            the given ticket
        :param latest: a list of the IDs of all tickets to be split from the
            given ticket, as specified by the most recent split action.

        The returned value is an updated count of splits from the current 
        ticket.

        """
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        # determine which splits should be deleted and which are new 
        deletions = [split for split in stored if split not in latest]
        additions = [split for split in latest if split not in stored]

        for split in deletions:
            cursor.execute("DELETE FROM ticket_split "
                           "WHERE ticket = %s AND split_to = %s",
                           (ticket.id, split,))

        for split in additions:
            cursor.execute("SELECT * FROM ticket_split "
                           "WHERE ticket = %s AND split_to = %s",
                           (ticket.id, split))

            stored = cursor.fetchone()

            if not stored:
                update_time = time.time()
                cursor.execute("INSERT INTO ticket_split "
                               "(ticket, split_to, split_at) "
                               "VALUES (%s, %s, %s)",
                               (ticket.id, split, update_time))

        db.commit()

        return len(stored) - len(deletions) + len(additions)
