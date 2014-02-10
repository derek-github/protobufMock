#encoding=gbk
#! /usr/bin/python


##
# @file mock_server.py
# @brief 
# @author Yang Yongqiang, yangyongqiang@sogou-inc.com
# @version 1.0
# @date 2013-01-10

# Copyright(C)
# by SOGOU-INC ADTQ
# All right reserved
# 


#from tool.log.log import Log
import string,os,sys
import socket
import struct
import subprocess
import re
import pickle
import select
import time
#加入系统路径，便于调试
file_path=os.path.dirname(os.path.abspath(__file__))
print "file_path : "+file_path 
sys.path.append(file_path+"/../")

from mock_lib.conf import get_conf_value
from mock_lib.header import x_server_header


class MockServer(object):
    '''通用Mock Server'''

##
# @brief __init__ 
#
# @param type : server or client 
#
# @return mock instance
    def __init__(self):
        '''准备工作：编译protobuf以及其他'''

        self.proto_file=get_conf_value('proto_buf','proto_buf')
        subprocess.call(["sh",file_path+"/../mock_protocol/body/create_pro_for_python.sh",self.proto_file])
        (self.file_name,self.ext)=os.path.splitext(self.proto_file)
        self.proto_import_module=self.file_name+"_pb2"
        #动态导入
        __import__("mock_protocol.body."+self.proto_import_module)
        self.proto_py = sys.modules["mock_protocol.body."+self.proto_import_module]
        #初始化proto_buf中的请求message
        self.request_proto=getattr(self.proto_py,get_conf_value('proto_buf','proto_request'))()
        #初始化proto_buf中的相应message
        self.response_proto=getattr(self.proto_py,get_conf_value('proto_buf','proto_response'))()
        #保存输出，由于是迭代输出，因此需要转成可变变量    
        self.out_put_str=[""]
        #标示启动的是server还是client，默认是server
        self.type = get_conf_value('mock_info','mode')
        #x-server的header
        self.header_data = x_server_header()
        #保存proto_buf的recv的message信息
        self.recv_proto_info={}
        #保存proto_buf的send的message信息
        self.send_proto_info={}
        #报头的设置
        self.header_type = int(get_conf_value('socket_conf','header'))
        #发送设置，报头和报体一起发送，或者报头和报体分开发送
        self.send_type = int(get_conf_value('socket_conf','send_type'))
        #协议设置(tcp/udp)
        self.socket_type = int(get_conf_value('socket_conf','socket_type'))
        #返回proto的验证方式，1是直接返回dict的形式（多用于client），二是将proto的dict对象dump到指定文件中
        self.interface_type = int(get_conf_value('out_put','show_proto_buf_info_style'))
        self.recv_dump_file = file_path+"/../"+str(get_conf_value('out_put','dump_file_path')).strip().strip("'")+"/"+str(get_conf_value('out_put','recv_dump_file')).strip().strip("'")
        self.send_dump_file = file_path+"/../"+str(get_conf_value('out_put','dump_file_path')).strip().strip("'")+"/"+str(get_conf_value('out_put','send_dump_file')).strip().strip("'")
        #server 启动等待client链接的timeout
        self.timeout= int(get_conf_value('socket_conf','timeout'))
        #server 是否循环发送消息
        self.server_loop = eval(get_conf_value('socket_conf','server_loop'))
        #server handler的时间
        self.server_hande_time = int(get_conf_value('mock_server','handle_time'))
        #server的返回信息或client的请求信息
        self.response_value = get_conf_value('mock_server','response_value')
        self.request_value = get_conf_value('mock_client','request_value')
        

##
# @brief send_proto_buf 
#
# @param value : proto_buf user-defined parameter's value
# 
# @return  protobuf serialize string 
    def send_proto_buf(self,value={}):
        '''发送prote_buf的入口'''
        self.__proto_buf(self.response_proto,value)
        #对proto进行序列化，直接可以进行socket网络传输
        return getattr(self.response_proto,"SerializeToString")()

    
##
# @brief __proto_buf 
#
# @param message_object
# @param value
#
# @return 
    def __proto_buf(self,message_object,value={}):
        '''将protobuf中的指定message进行序列化，对value中指定的值进行更新'''
        for key in value.keys():
            self.message_item_type=type(getattr(message_object,key)).__name__
            if self.message_item_type in ('str','int','float','bool','long'):
                setattr(message_object,key,eval(str(self.message_item_type)+"('"+str(value[key])+"')"))
                continue
            #repeat 组合
            if self.message_item_type == "RepeatedCompositeFieldContainer":
                for repeat_item in value[key]:
                    self.message_object_add = getattr(message_object,key).add()
                    self.__proto_buf(self.message_object_add,repeat_item)
                continue
            #repeat单个值 value[key]对应的应该是一个list
            if self.message_item_type == "RepeatedScalarFieldContainer":
                if not isinstance(value[key],list): 
                    raise "the parameter : "+str(key)+" in protobuf the value type should be list not "+type(value[key]).__name__
                else: getattr(message_object,key).extend(value[key]) 

            else :
                self.message_object_proto = getattr(message_object,key)
                self.__proto_buf(self.message_object_proto,value[key])
                continue
    
        return 



##
# @brief __list_proto_buf 
#
# @param proto_buf_instance
# @param result_info
#
# @return 
    def __list_proto_buf(self,proto_buf_instance,result_info={}):
        '''输出proto_buf的内容,输出内容放在out_put_str这个全局变量中'''
        items = filter(lambda x : re.match('^[a-z]',x) , dir(proto_buf_instance)) 
        for i in items:
            #正常处理
            if isinstance(getattr(proto_buf_instance,i),(int,str,bool,float,long)):
                self.out_put_str[0] += str(i)+" : "+str(getattr(proto_buf_instance,i))+"\n"
                result_info[str(i)]=str(getattr(proto_buf_instance,i))
            #对repeat 的组合 进行处理
            elif type(getattr(proto_buf_instance,i)).__name__ == "RepeatedCompositeFieldContainer":
                self.out_put_str[0] += str(i) + " : \n"
                self.out_put_str[0] += '*'*40+"\n"
                result_info[str(i)]=[]
                for vec_item in getattr(proto_buf_instance,i):
                    #self.out_put_str[0] += '*'*20+"\n"
                    self.repeat_info_temp={}
                    self.__list_proto_buf(vec_item,self.repeat_info_temp)
                    result_info[str(i)].append(self.repeat_info_temp)
                    self.out_put_str[0] += '+'*30+"\n"
                self.out_put_str[0] += '*'*40+"\n"
            #对repeat 的单个值 进行处理
            elif type(getattr(proto_buf_instance,i)).__name__ == "RepeatedScalarFieldContainer":
                self.out_put_str[0] += str(i) + " : \n"
                self.out_put_str[0] += '*'*40+"\n"
                self.list_info_temp=[]
                for list_item in getattr(proto_buf_instance,i):
                    self.out_put_str[0] += str(list_item)+"\n"
                    self.list_info_temp.append(str(list_item))
                self.out_put_str[0] += '*'*40+"\n"
                result_info[str(i)]=self.list_info_temp
                continue
            #message中定义message，跳过
            elif type(getattr(proto_buf_instance,i)).__name__=="GeneratedProtocolMessageType":
                    continue
            #对一个message内嵌套另一个message进行处理
            else :
                self.out_put_str[0] += str(i) + "  : \n"
                self.out_put_str[0] += '*'*40+"\n"
                result_info[str(i)]={}
                self.__list_proto_buf(getattr(proto_buf_instance,i),result_info[str(i)])
                self.out_put_str[0] += '*'*40+"\n"

##
# @brief list_proto 
#
# @param message
# @param message_info
#
# @return 
    def list_proto(self,message,message_info):
        '''打印proto详细信息入口'''
        #object=getattr(message,function)()
        self.__list_proto_buf(message,message_info)
        self.out_put_str[0] += "#"*50+"\n"
        print self.out_put_str[0]
        #清空
        self.out_put_str[0]=""



    def __proto_recv_handler_udp(self,socket,header_type):
        '''udp server接收数据'''
        if 0 == header_type:
            print "recv.."
            self.data_recv,addr = socket.recvfrom(int(get_conf_value('mock_info','BUFFERSIZE')))
            getattr(self.request_proto,"ParseFromString")(self.data_recv)
            self.list_proto(self.request_proto,self.recv_proto_info)
            return addr
        elif 1 == header_type:
            self.data_recv,addr = socket.recvfrom(int(get_conf_value('mock_info','BUFFERSIZE')))
            if len(self.data_recv) > 36:
                self.data_recv = self.data_recv[36:]
            getattr(self.request_proto,"ParseFromString")(self.data_recv)
            self.list_proto(self.request_proto,self.recv_proto_info)
            return addr
        else:
            print '[conf error] header_type.'
            

    def __proto_send_handler_udp(self,socket,addr,header_type,value):
        '''udp server发送数据'''
        if 0 == header_type:
            self.data_send = self.send_proto_buf(value)
        elif 1 == header_type:
            self.data_send = self.header_data.package_header(len(self.data_send))+self.data_send
        else:
            print '[conf error] header_type.'
            return 
        ret = socket.sendto("%s"%self.data_send,addr)
        if ret < 0:
            print '[udp socket] send error.'


##
# @brief __proto_recv_handler 
#
# @param connect
# @param header_type
# @param send_type
# @param value
#
# @return 
    def __proto_recv_handler(self,connect,header_type,send_type,value={}):
        '''接受proto_buf的处理函数'''
        #server接受请求处理
        #没有header的情况下，接受到的data就是body
        if 0 == header_type :
            self.data = connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
            #打印request的protobuf的信息
            getattr(self.request_proto,"ParseFromString")(self.data)
            self.list_proto(self.request_proto,self.recv_proto_info)

        #如果xserver的header,则需要去掉header部分，然后对body进行解析
        elif 1 == header_type :
            #如果报头和报体一起发送,就只接收一次就行了
            if 2 == send_type :
                self.data = connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
                if len(self.data) >= 36 :
                    self.data = self.data[36:]
                    self.out_put_str[0] += "the request protobuf items as below: \n"

            #如果分开发送就要通过接受的报头的报体的len字段就行循环接受，指导所有数据都接收完成
            elif 1 == send_type :
                self.data=""
                while len(self.data) < 36 :
                    self.data += connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
                #报头接收成功
                self.header_recv = self.data[:36]
                self.header_item = self.header_data.unpackage_header(self.header_recv)
                self.out_put_str[0] += "recv_header : \n"
                self.out_put_str[0] += "="*50+"\n"
                for i in self.header_item.keys(): 
                    self.out_put_str[0] += str(i) + " : "+str(self.header_item[i])+"\n"
                self.out_put_str[0] += "="*50+"\n"
                self.out_put_str[0] += "the request protobuf items as below: \n"
                self.out_put_str[0] += "#"*50+"\n"
                self.data=self.data[36:]
                #body很大的时候，会分开发送多个数据包，确保接收成功
                while len(self.data) < int(self.header_item["body_len"]):
                    self.data += connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
            
            #打印request的protobuf的信息
            print "data == "+str(self.data)
            print "len(data) == "+str(len(self.data))
            getattr(self.request_proto,"ParseFromString")(self.data)
            self.list_proto(self.request_proto,self.recv_proto_info)


        elif 2 == header_type:
            #TODO: 自定义header
            print "TODO"

##
# @brief __proto_send_handler 
#
# @param connect
# @param header_type
# @param send_type
# @param value
#
# @return 
    def __proto_send_handler(self,connect,header_type,send_type,value={}):
        '''处理proto_buf的发送函数'''
        self.data = self.send_proto_buf(value)
        if 0 == header_type :
            pass
        #如果xserver的header,则需要加上header部分，然后发送
        elif 1 == header_type :
            #send_type是分开发送的情况，后续考虑 TODO 
            self.data = self.header_data.package_header(len(self.data))+self.data 
        connect.send(self.data)
        self.list_proto(self.response_proto,self.send_proto_info)

    def __server_start(self,value,header_type,send_type,socket_type):
        '''启动server,value是对返回的proto buf的值进行设置'''
        if 1 == socket_type:
            self.__server_start_tcp(value,header_type,send_type)
        elif 2 == socket_type:
            self.__server_start_udp(value,header_type)
        else:
            print '[conf error!] socket_type'

    def __server_start_udp(self,value,header_type):
        '''udp server'''
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.socket_server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.ADDR=('',int(get_conf_value('mock_server','listen_port')))
        self.socket_server.bind(self.ADDR)
        self.tran_addr=()
        while True:
            self.infds,self.outfds,self.errfds = select.select([self.socket_server,],[],[],self.timeout)
            if 0 == len(self.infds):
                raise "wait for client connection is timeout!!!"
            #udp server接收数据
            self.tran_addr=self.__proto_recv_handler_udp(self.socket_server,header_type)

            #模拟处理时间
            time.sleep(self.server_hande_time)

            #udp server发送数据
            self.__proto_send_handler_udp(self.socket_server,self.tran_addr,header_type,value)

            if not self.server_loop:
                self.socket_server.close()
                break

        print "bye server."


##
# @brief __server_start_tcp
#
# @param value
# @param header_type
# @param send_type
#
# @return 
    def __server_start_tcp(self,value,header_type,send_type):
        '''tcp server'''
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #关闭后立即释放端口
        self.socket_server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
        self.ADDR=('',int(get_conf_value('mock_server','listen_port')))
        self.socket_server.bind(self.ADDR)
        self.socket_server.listen(10)
        while True:

            self.infds,self.outfds,self.errfds = select.select([self.socket_server,],[],[],self.timeout)
    
            if 0 == len(self.infds):
    
                raise "wait for client connection is timeout!!!"
    
    
            (self.server_conn,self.client_addr) = self.socket_server.accept()
            #接受处理函数
            self.out_put_str[0] += "recved from client: "+str(self.client_addr)+ "\n"
            self.__proto_recv_handler(connect=self.server_conn,header_type=header_type,send_type=send_type,value=value)
            #server - send response to client
            self.out_put_str[0] += "\n"*3

            #等待时间长，模拟处理时间
            time.sleep(self.server_hande_time)

            #处理发送数据
            self.__proto_send_handler(connect=self.server_conn,header_type=header_type,send_type=send_type,value=value)        
            #send....
            if not self.server_loop : 
                self.socket_server.close()
                break
        print "bye server~~"


    def __client_start(self,value,header_type,send_type,socket_type):
        if 1 == socket_type:
            self.__client_start_tcp(value,header_type,send_type)
        elif 2 == socket_type:
            self.__client_start_udp(value,header_type)
        else:
            print "[conf error!] socket_type"


    def __client_start_udp(self,value,header_type):
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_client.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.ADDR=(str(get_conf_value('mock_client','server_ip')),int(get_conf_value('mock_client','server_port')))
        #self.socket_server.bind(self.ADDR)
        #self.socket_server.listen(10)

        self.__proto_send_handler_udp(self.socket_client,self.ADDR,header_type,value)
        self.__proto_recv_handler_udp(self.socket_client,header_type)

        self.socket_client.close()

    
##
# @brief __client_start 
#
# @param value
# @param header_type
# @param send_type
#
# @return 
    def __client_start_tcp(self,value,header_type,send_type):
        '''启动客户端，value是对请求的proto_buf的值进行设置'''
        self.socket_client=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ADDR=(get_conf_value('mock_client','server_ip'),int(get_conf_value('mock_client','server_port')))
        self.socket_client.connect(self.ADDR)
        #处理发送数据
        self.__proto_send_handler(connect=self.socket_client,header_type=header_type,send_type=send_type,value=value)        
        
        self.out_put_str[0] += "\n"*3
        
        #接收处理函数
        self.out_put_str[0] += "recved from server: "+str(self.ADDR[0])+ "\n"
        self.__proto_recv_handler(connect=self.socket_client,header_type=header_type,send_type=send_type,value=value)
        self.socket_client.close()
    
##
# @brief run 
#
# @param value
#
# @return 
    def run(self,type,value={},timeout=None,server_loop=None):
        '''启动桩，发送或接受报文'''
        self.type=type
        if timeout : self.timeout = int(timeout)
        if server_loop : self.server_loop = bool(server_loop)
        if self.type == 'server' : 
            self.timeout=timeout
            self.__server_start(value,self.header_type,self.send_type,self.socket_type)
            #如果是直接等待返回的
            if self.interface_type == 1:
                return self.send_proto_info
            #如果是dump的话 直接将proto中的信息已字典的形式dump到文件中
            elif self.interface_type == 2: 
                f = open(self.send_dump_file,'wb') 
                pickle.dump(self.send_proto_info,f)
                #pickle.dump(self.recv_proto_info,f)
                f.close()
                return None


        if self.type == 'client' : 
            #互掉一下，client的发送和接受正好和server相反
            self.request_proto, self.response_proto = self.response_proto,self.request_proto
            self.__client_start(value,self.header_type,self.send_type,self.socket_type)
            #如果是直接等待返回的
            if self.interface_type == 1:
                return self.recv_proto_info
            #如果是dump的话 直接将proto中的信息已字典的形式dump到文件中
            elif self.interface_type == 2: 
                f = open(self.recv_dump_file,'wb')
                pickle.dump(self.recv_proto_info,f)
                #pickle.dump(self.send_proto_info,f)
                f.close()
                return None

        else: print "error type not in [server ,  client]"


    def get_request_proto_info(self):
        '''拿到request的dict信息'''
        if self.interface_type == 1: return server.recv_proto_info
        if self.interface_type == 2: 
            f = open(self.recv_dump_file,'rb')
            return pickle.load(f)
        return None
    
    
    def get_response_proto_info(self):
        '''拿到response的dict信息'''
        if self.interface_type == 1: return server.send_proto_info
        if self.interface_type == 2: 
            f = open(self.send_dump_file,'rb')
            return pickle.load(f)
        return None

if __name__=="__main__":

    #response_value={"version":1,"rdr":1,"errno_xx":0,"clickid":"0f0c5990e86a1365ffffffff8831645f","rule_ret":"0,0,0","pass_ret":"1,1,1","extend_item":""}
    #request_value={}
    server = MockServer()
    print '+++++++++++++++'
    if 1 == int(server.type):
        print server.run('server',eval(server.response_value),server_loop=True,timeout=100)
    elif 2 == int(server.type):
        print server.run('client',request_value,server_loop=True,timeout=100)
    print "+++++++++++++++++"
    print "Bye"

    #print '++++++++get request  from pickle ++++++++++'
    #print server.get_request_proto_info()
    #print '++++++++get response  from pickle ++++++++++'
    #print server.get_response_proto_info()
