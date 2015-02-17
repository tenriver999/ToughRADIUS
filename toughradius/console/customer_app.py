#!/usr/bin/env python
#coding:utf-8
import sys,os
from autobahn.twisted import choosereactor
choosereactor.install_optimal_reactor(True)
from twisted.python import log
from bottle import request
from bottle import response
from bottle import TEMPLATE_PATH,MakoTemplate
from bottle import run as runserver
from toughradius.console.customer.customer import app as mainapp
from toughradius.console.libs import sqla_plugin,utils
from toughradius.console.libs.smail import mail
from toughradius.console.websock import websock
from toughradius.console import base
from toughradius.console import models
from toughradius.console.base import (
    get_cookie,
    set_cookie,
    get_param_value,
    get_member_by_name,
    get_account_by_number,
    get_online_status
)
import functools
import time


def init_application(config):
    log.startLogging(sys.stdout)  
    log.msg("start init application...")
    TEMPLATE_PATH.append(os.path.join(os.path.split(__file__)[0],"customer/views/"))
    ''' install plugins'''
    engine,metadata = models.get_engine(config)
    sqla_pg = sqla_plugin.Plugin(engine,metadata,keyword='db',create=False,commit=False,use_kwargs=False)
    session = sqla_pg.new_session()
    _sys_param_value = functools.partial(get_param_value,session)
    _get_member_by_name = functools.partial(get_member_by_name,session)
    _get_account_by_number = functools.partial(get_account_by_number,session)
    _get_online_status = functools.partial(get_online_status,session)
    MakoTemplate.defaults.update(**dict(
        get_cookie = get_cookie,
        fen2yuan = utils.fen2yuan,
        fmt_second = utils.fmt_second,
        bb2mb = utils.bb2mb,
        bbgb2mb = utils.bbgb2mb,
        kb2mb = utils.kb2mb,
        mb2kb = utils.mb2kb,
        sec2hour = utils.sec2hour,
        request = request,
        sys_param_value = _sys_param_value,
        get_member = _get_member_by_name,
        get_account = _get_account_by_number,
        is_online = _get_online_status
    ))
    
    mail.setup(
        server=_sys_param_value('smtp_server'),
        user=_sys_param_value('smtp_user'),
        pwd=_sys_param_value('smtp_pwd'),
        fromaddr=_sys_param_value('smtp_user'),
        sender=_sys_param_value('smtp_sender')
    )

    websock.connect(
        _sys_param_value('radiusd_address'),
        _sys_param_value('radiusd_admin_port')
    )
    
    mainapp.install(sqla_pg)


###############################################################################
# run server                                                                 
###############################################################################

def main():
    import argparse,ConfigParser
    parser = argparse.ArgumentParser()
    parser.add_argument('-http','--httpport', type=int,default=0,dest='httpport',help='http port')
    parser.add_argument('-d','--debug', action='store_true',default=False,dest='debug',help='debug')
    parser.add_argument('-c','--conf', type=str,default="../radiusd.conf",dest='conf',help='conf file')
    args =  parser.parse_args(sys.argv[1:])

    if not args.conf or not os.path.exists(args.conf):
        print 'no config file user -c or --conf cfgfile'
        return

    # read config file
    config = ConfigParser.ConfigParser()
    config.read(args.conf)
    
    # update aescipher,timezone
    utils.aescipher.setup(config.get('DEFAULT','secret'))
    base.scookie.setup(config.get('DEFAULT','secret'))
    utils.update_tz(config.get('DEFAULT','tz'))

    try:
        init_application(config)
        runserver(
            mainapp, host='0.0.0.0', 
            port=args.httpport or config.get("customer","port") ,
            debug=config.getboolean('DEFAULT','debug')  ,
            reloader=False,
            server="twisted"
        )
    except:
        log.err()

if __name__ == "__main__":
    main()