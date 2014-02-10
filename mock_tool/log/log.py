#coding=UTF-8

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from decorator import singleton
from decorator import inspect_code_line
import logging
import logging.handlers
import time
import inspect


class LOG(object):
    logger=logging.getLogger()
    @singleton
    def __init__(self,file="/search/Django/django_site_zabbix/django_site_zabbix/log/debug.log",level=logging.NOTSET):
        #self.handler = logging.FileHandler(file)
        self.handler = logging.handlers.TimedRotatingFileHandler(filename=file,when="H", backupCount=24*7)
        LOG.logger.addHandler(self.handler)
        LOG.logger.setLevel(level)
 

    @inspect_code_line
    def critical(self,msg):
        '''critical'''
        return (msg,LOG.logger,"critical")

    @inspect_code_line
    def error(self,msg):
        '''error'''
        return (msg,LOG.logger,"error")

    @inspect_code_line
    def info(self,msg):
        '''info'''
        return (msg,LOG.logger,"info")



if __name__=="__main__":
    LOG("/search/log").error("错误error示例")
    time.sleep(1)
    LOG().info("提示info示例")
    time.sleep(1)
    LOG().critical("严重错误critical示例")
