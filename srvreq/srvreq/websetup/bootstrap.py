# -*- coding: utf-8 -*-
"""Setup the srvreq application"""
from __future__ import print_function, unicode_literals
import transaction
from srvreq import model


def bootstrap(command, conf, vars):
    """Place any commands to setup srvreq here"""

    # <websetup.bootstrap.before.auth
    from sqlalchemy.exc import IntegrityError
    try:
        '''
        u = model.User()
        u.user_name = 'manager'
        u.display_name = 'Example manager'
        u.email_address = 'manager@somedomain.com'
        u.password = 'managepass'
    
        model.DBSession.add(u)
    
        g = model.Group()
        g.group_name = 'managers'
        g.display_name = 'Managers Group'
    
        g.users.append(u)
    
        model.DBSession.add(g)
    
        p = model.Permission()
        p.permission_name = 'manage'
        p.description = 'This permission gives an administrative right'
        p.groups.append(g)
    
        model.DBSession.add(p)
    
        u1 = model.User()
        u1.user_name = 'editor'
        u1.display_name = 'Example editor'
        u1.email_address = 'editor@somedomain.com'
        u1.password = 'editpass'
    
        model.DBSession.add(u1) 
        '''

        # Add default value for OCI settings
        model.DBSession.add(model.Setting(name="admin_username",
                                          value="vescosof@broadsoft.com"))
        model.DBSession.add(model.Setting(name="admin_password",
                                          value="Welcome2013"))
        model.DBSession.add(model.Setting(name="oci_root",
                                          value="https://xsp1.ihs.broadsoft.com"))
        model.DBSession.add(model.Setting(name="xsp_username",
                                          value=""))
        model.DBSession.add(model.Setting(name="xsp_password",
                                          value=""))
        model.DBSession.add(model.Setting(name="device_type",
                                          value="Connect - Mobile"))
        model.DBSession.flush()
        transaction.commit()
    except IntegrityError:
        print('Warning, there was a problem adding your settings data, '
              'it may have already been added:')
        import traceback
        print(traceback.format_exc())
        transaction.abort()
        print('Continuing with bootstrapping...')

    '''
    try:
        # Add supported OCIP Requests
        model.DBSession.add(model.Request(name="group_device_get_custom_tags",
                                          display_name="GroupAccessDeviceCustomTagGetListRequest",
                                          type="ocip"))

        # Add supported XSP Requests
        model.DBSession.add(model.Request(name="get_device_name_by_type",
                                          display_name="profile/device",
                                          type="xsp"))


        model.DBSession.flush()
        transaction.commit()
    except IntegrityError:
        print('Warning, there was a problem adding your request data, '
              'it may have already been added:')
        import traceback
        print(traceback.format_exc())
        transaction.abort()
        print('Continuing with bootstrapping...')
    '''

    # <websetup.bootstrap.after.auth>
