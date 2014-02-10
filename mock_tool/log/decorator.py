#coding=UTF-8
import inspect
import time
import sys

def singleton(cls):
    '''单例的装饰器'''
    instances={}
    def _singleton(*args,**kw):
        if cls not in instances:
            instances[cls]=cls(*args, **kw)
        return instances[cls]
    return _singleton


def inspect_code_line(func):
    '''动态获取当前行号'''
    def function_decode(*args,**kw):
        '''装饰函数'''
        try:
            raise Exception
        except:
            f = sys.exc_info()[2].tb_frame.f_back
            filename = f.f_code.co_filename
            function = f.f_code.co_name
            line = f.f_lineno
    
        (msg, logger , log_type) = func(*args,**kw)
        msg = "["+str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))+"] ["+log_type.upper()+"] ["+filename+"] ["+str(function)+":"+str(line)+"] "+msg
        return getattr(logger,log_type)(msg)

    return function_decode
