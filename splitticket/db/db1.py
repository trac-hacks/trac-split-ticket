from trac.db import Table, Column, Index, DatabaseManager


def do_upgrade(env):
    """ Upgrade the database schema so that it is compatible with version 1 
    of the plugin. 

    :param env: the current Trac environment

    """
    db_connector, _ = DatabaseManager(env)._get_connector()
    db = env.get_db_cnx()
    cursor = db.cursor()

    # add 'ticket_split' table to the schema
    split_ticket_table = Table('ticket_split', key=('ticket', 'split_to'))[
                             Column('ticket', type='int'),
                             Column('split_to', type='int'),
                             Column('split_at', type='int')
                         ]

    for statement in db_connector.to_sql(split_ticket_table):
        cursor.execute(statement)
    
    # update stored schema version for the plugin
    sql = ("INSERT INTO system(name, value) "
           "VALUES ('splitticket_plugin_version', '1')")

    cursor.execute(sql)
