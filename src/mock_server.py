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
#����ϵͳ·�������ڵ���
file_path=os.path.dirname(os.path.abspath(__file__))
print "file_path : "+file_path 
sys.path.append(file_path+"/../")

from mock_lib.conf import get_conf_value
from mock_lib.header import x_server_header


class MockServer(object):
    '''ͨ��Mock Server'''

##
# @brief __init__ 
#
# @param type : server or client 
#
# @return mock instance
    def __init__(self):
        '''׼������������protobuf�Լ�����'''

        self.proto_file=get_conf_value('proto_buf','proto_buf')
        subprocess.call(["sh",file_path+"/../mock_protocol/body/create_pro_for_python.sh",self.proto_file])
        (self.file_name,self.ext)=os.path.splitext(self.proto_file)
        self.proto_import_module=self.file_name+"_pb2"
        #��̬����
        __import__("mock_protocol.body."+self.proto_import_module)
        self.proto_py = sys.modules["mock_protocol.body."+self.proto_import_module]
        #��ʼ��proto_buf�е�����message
        self.request_proto=getattr(self.proto_py,get_conf_value('proto_buf','proto_request'))()
        #��ʼ��proto_buf�е���Ӧmessage
        self.response_proto=getattr(self.proto_py,get_conf_value('proto_buf','proto_response'))()
        #��������������ǵ�������������Ҫת�ɿɱ����    
        self.out_put_str=[""]
        #��ʾ��������server����client��Ĭ����server
        self.type = get_conf_value('mock_info','mode')
        #x-server��header
        self.header_data = x_server_header()
        #����proto_buf��recv��message��Ϣ
        self.recv_proto_info={}
        #����proto_buf��send��message��Ϣ
        self.send_proto_info={}
        #��ͷ������
        self.header_type = int(get_conf_value('socket_conf','header'))
        #�������ã���ͷ�ͱ���һ���ͣ����߱�ͷ�ͱ���ֿ�����
        self.send_type = int(get_conf_value('socket_conf','send_type'))
        #Э������(tcp/udp)
        self.socket_type = int(get_conf_value('socket_conf','socket_type'))
        #����proto����֤��ʽ��1��ֱ�ӷ���dict����ʽ��������client�������ǽ�proto��dict����dump��ָ���ļ���
        self.interface_type = int(get_conf_value('out_put','show_proto_buf_info_style'))
        self.recv_dump_file = file_path+"/../"+str(get_conf_value('out_put','dump_file_path')).strip().strip("'")+"/"+str(get_conf_value('out_put','recv_dump_file')).strip().strip("'")
        self.send_dump_file = file_path+"/../"+str(get_conf_value('out_put','dump_file_path')).strip().strip("'")+"/"+str(get_conf_value('out_put','send_dump_file')).strip().strip("'")
        #server �����ȴ�client���ӵ�timeout
        self.timeout= int(get_conf_value('socket_conf','timeout'))
        #server �Ƿ�ѭ��������Ϣ
        self.server_loop = eval(get_conf_value('socket_conf','server_loop'))
        #server handler��ʱ��
        self.server_hande_time = int(get_conf_value('mock_server','handle_time'))
        #server�ķ�����Ϣ��client��������Ϣ
        self.response_value = get_conf_value('mock_server','response_value')
        self.request_value = get_conf_value('mock_client','request_value')
        

##
# @brief send_proto_buf 
#
# @param value : proto_buf user-defined parameter's value
# 
# @return  protobuf serialize string 
    def send_proto_buf(self,value={}):
        '''����prote_buf�����'''
        self.__proto_buf(self.response_proto,value)
        #��proto�������л���ֱ�ӿ��Խ���socket���紫��
        return getattr(self.response_proto,"SerializeToString")()

    
##
# @brief __proto_buf 
#
# @param message_object
# @param value
#
# @return 
    def __proto_buf(self,message_object,value={}):
        '''��protobuf�е�ָ��message�������л�����value��ָ����ֵ���и���'''
        for key in value.keys():
            self.message_item_type=type(getattr(message_object,key)).__name__
            if self.message_item_type in ('str','int','float','bool','long'):
                setattr(message_object,key,eval(str(self.message_item_type)+"('"+str(value[key])+"')"))
                continue
            #repeat ���
            if self.message_item_type == "RepeatedCompositeFieldContainer":
                for repeat_item in value[key]:
                    self.message_object_add = getattr(message_object,key).add()
                    self.__proto_buf(self.message_object_add,repeat_item)
                continue
            #repeat����ֵ value[key]��Ӧ��Ӧ����һ��list
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
        '''���proto_buf������,������ݷ���out_put_str���ȫ�ֱ�����'''
        items = filter(lambda x : re.match('^[a-z]',x) , dir(proto_buf_instance)) 
        for i in items:
            #��������
            if isinstance(getattr(proto_buf_instance,i),(int,str,bool,float,long)):
                self.out_put_str[0] += str(i)+" : "+str(getattr(proto_buf_instance,i))+"\n"
                result_info[str(i)]=str(getattr(proto_buf_instance,i))
            #��repeat ����� ���д���
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
            #��repeat �ĵ���ֵ ���д���
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
            #message�ж���message������
            elif type(getattr(proto_buf_instance,i)).__name__=="GeneratedProtocolMessageType":
                    continue
            #��һ��message��Ƕ����һ��message���д���
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
        '''��ӡproto��ϸ��Ϣ���'''
        #object=getattr(message,function)()
        self.__list_proto_buf(message,message_info)
        self.out_put_str[0] += "#"*50+"\n"
        print self.out_put_str[0]
        #���
        self.out_put_str[0]=""



    def __proto_recv_handler_udp(self,socket,header_type):
        '''udp server��������'''
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
        '''udp server��������'''
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
        '''����proto_buf�Ĵ�����'''
        #server����������
        #û��header������£����ܵ���data����body
        if 0 == header_type :
            self.data = connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
            #��ӡrequest��protobuf����Ϣ
            getattr(self.request_proto,"ParseFromString")(self.data)
            self.list_proto(self.request_proto,self.recv_proto_info)

        #���xserver��header,����Ҫȥ��header���֣�Ȼ���body���н���
        elif 1 == header_type :
            #�����ͷ�ͱ���һ����,��ֻ����һ�ξ�����
            if 2 == send_type :
                self.data = connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
                if len(self.data) >= 36 :
                    self.data = self.data[36:]
                    self.out_put_str[0] += "the request protobuf items as below: \n"

            #����ֿ����;�Ҫͨ�����ܵı�ͷ�ı����len�ֶξ���ѭ�����ܣ�ָ���������ݶ��������
            elif 1 == send_type :
                self.data=""
                while len(self.data) < 36 :
                    self.data += connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
                #��ͷ���ճɹ�
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
                #body�ܴ��ʱ�򣬻�ֿ����Ͷ�����ݰ���ȷ�����ճɹ�
                while len(self.data) < int(self.header_item["body_len"]):
                    self.data += connect.recv(int(get_conf_value('mock_info','BUFFERSIZE')))
            
            #��ӡrequest��protobuf����Ϣ
            print "data == "+str(self.data)
            print "len(data) == "+str(len(self.data))
            getattr(self.request_proto,"ParseFromString")(self.data)
            self.list_proto(self.request_proto,self.recv_proto_info)


        elif 2 == header_type:
            #TODO: �Զ���header
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
        '''����proto_buf�ķ��ͺ���'''
        self.data = self.send_proto_buf(value)
        if 0 == header_type :
            pass
        #���xserver��header,����Ҫ����header���֣�Ȼ����
        elif 1 == header_type :
            #send_type�Ƿֿ����͵�������������� TODO 
            self.data = self.header_data.package_header(len(self.data))+self.data 
        connect.send(self.data)
        self.list_proto(self.response_proto,self.send_proto_info)

    def __server_start(self,value,header_type,send_type,socket_type):
        '''����server,value�ǶԷ��ص�proto buf��ֵ��������'''
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
            #udp server��������
            self.tran_addr=self.__proto_recv_handler_udp(self.socket_server,header_type)

            #ģ�⴦��ʱ��
            time.sleep(self.server_hande_time)

            #udp server��������
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
        #�رպ������ͷŶ˿�
        self.socket_server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
        self.ADDR=('',int(get_conf_value('mock_server','listen_port')))
        self.socket_server.bind(self.ADDR)
        self.socket_server.listen(10)
        while True:

            self.infds,self.outfds,self.errfds = select.select([self.socket_server,],[],[],self.timeout)
    
            if 0 == len(self.infds):
    
                raise "wait for client connection is timeout!!!"
    
    
            (self.server_conn,self.client_addr) = self.socket_server.accept()
            #���ܴ�����
            self.out_put_str[0] += "recved from client: "+str(self.client_addr)+ "\n"
            self.__proto_recv_handler(connect=self.server_conn,header_type=header_type,send_type=send_type,value=value)
            #server - send response to client
            self.out_put_str[0] += "\n"*3

            #�ȴ�ʱ�䳤��ģ�⴦��ʱ��
            time.sleep(self.server_hande_time)

            #����������
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
        '''�����ͻ��ˣ�value�Ƕ������proto_buf��ֵ��������'''
        self.socket_client=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ADDR=(get_conf_value('mock_client','server_ip'),int(get_conf_value('mock_client','server_port')))
        self.socket_client.connect(self.ADDR)
        #����������
        self.__proto_send_handler(connect=self.socket_client,header_type=header_type,send_type=send_type,value=value)        
        
        self.out_put_str[0] += "\n"*3
        
        #���մ�����
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
        '''����׮�����ͻ���ܱ���'''
        self.type=type
        if timeout : self.timeout = int(timeout)
        if server_loop : self.server_loop = bool(server_loop)
        if self.type == 'server' : 
            self.timeout=timeout
            self.__server_start(value,self.header_type,self.send_type,self.socket_type)
            #�����ֱ�ӵȴ����ص�
            if self.interface_type == 1:
                return self.send_proto_info
            #�����dump�Ļ� ֱ�ӽ�proto�е���Ϣ���ֵ����ʽdump���ļ���
            elif self.interface_type == 2: 
                f = open(self.send_dump_file,'wb') 
                pickle.dump(self.send_proto_info,f)
                #pickle.dump(self.recv_proto_info,f)
                f.close()
                return None


        if self.type == 'client' : 
            #����һ�£�client�ķ��ͺͽ������ú�server�෴
            self.request_proto, self.response_proto = self.response_proto,self.request_proto
            self.__client_start(value,self.header_type,self.send_type,self.socket_type)
            #�����ֱ�ӵȴ����ص�
            if self.interface_type == 1:
                return self.recv_proto_info
            #�����dump�Ļ� ֱ�ӽ�proto�е���Ϣ���ֵ����ʽdump���ļ���
            elif self.interface_type == 2: 
                f = open(self.recv_dump_file,'wb')
                pickle.dump(self.recv_proto_info,f)
                #pickle.dump(self.send_proto_info,f)
                f.close()
                return None

        else: print "error type not in [server ,  client]"


    def get_request_proto_info(self):
        '''�õ�request��dict��Ϣ'''
        if self.interface_type == 1: return server.recv_proto_info
        if self.interface_type == 2: 
            f = open(self.recv_dump_file,'rb')
            return pickle.load(f)
        return None
    
    
    def get_response_proto_info(self):
        '''�õ�response��dict��Ϣ'''
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
