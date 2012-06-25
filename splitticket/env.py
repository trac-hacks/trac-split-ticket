from pkg_resources import resource_filename

from trac.config import Configuration
from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant


REQUIRED_DB_VERSION = 1


class SplitTicketEnvironment(Component):
    
    implements(IEnvironmentSetupParticipant)

    # IEnvironmentSetupParticipant methods

    def environment_created(self):
        pass

    def environment_needs_upgrade(self, db):
        return self._stored_db_version(db) != REQUIRED_DB_VERSION

    def upgrade_environment(self, db):
        # add custom workflow to trac.ini
        self._update_ticket_workflow()
    
        db_version = self._stored_db_version(db)

        # perform incremental upgrades of the database
        for version in range(db_version, REQUIRED_DB_VERSION):
            self._perform_db_upgrade(db, version + 1)

    # Internal methods
   
    def _update_ticket_workflow(self):
        """ Add the plugin to the list of ticket workflow participants 
        defined in the Trac environment configuration.

        """
        workflow_participants = self.config.get('ticket', 'workflow').split(',')
        
        if 'SplitTicketWorkflow' not in workflow_participants:
            workflow_participants.append('SplitTicketWorkflow')
            
        self.config.set('ticket', 'workflow', ', '.join(workflow_participants))
        self.config.save()

    def _stored_db_version(self, db):
        """ Return the most recent database schema version for the plugin. If 
        no previous schema version has been stored by the plugin, a value of
        0 (zero) is returned.

        :param db: the database used by the current Trac environment

        """
        cursor = db.cursor()

        cursor.execute("SELECT value FROM system WHERE name = %s", 
                       ('splitticket_plugin_version',))

        try:
            version = cursor.fetchone()[0]
            return int(version)
        except:
            return 0

    def _perform_db_upgrade(self, db, version):
        """ Upgrade the database schema to a new version. Upgrade logic is 
        defined in a version-specific upgrade module.

        :param db: the database used by the current Trac environment
        :param version: the schema version targeted in this upgrade

        """
        upgrade_module = __import__('splitticket.db.%s' % ('db%i' % version),
                                    globals(), locals(), ['do_upgrade'])

        upgrade_module.do_upgrade(self.env)
