#coding=gbk
import struct
import socket


class x_server_header(object) :

    '''
    Ŀǰ��ͨ�������ʽ���б����Ŀռ���������ɽ���������Ķ�̬���ء�
    ͷ�ṹ����
           unit16_t id, //id  1
           unit16_t version, //�汾�� 1
           unit32_t log_id, //��apche������logid���ᴩһ��������������罻�� 111
           char provider[16], //�ͻ��˱�ʵ����"client" 
           uint32_t magic_num //�����ʾ��һ��������ʼ 0xffee7799
           unit32_t reserved; //����
           unit32_t body_len; //head��������ܳ��ȣ�Ҳ����protobuf���кź�ĳ���
    '''
        
    def __init__(self,id=1,version=1,log_id=111,provider='client',magic_num=socket.htonl(0xffee7799),reserved=0):
        '''����ʵ����ʱ����Ҫ����body_len�������'''
        self.id=id
        self.version=version
        self.log_id=log_id
        self.provider=provider
        self.magic_num=magic_num
        self.reserved=reserved

    def package_header(self,body_len):
        '''��ת���������ٽ���struct'''
        self.id = socket.htons(self.id)
        self.version = socket.htons(self.version)
        self.log_id = socket.htonl(self.log_id)
        self.reserved = socket.htons(self.reserved)
        self.body_len = socket.htonl(body_len)

        #���л�������
        return struct.pack("!HHI16sIII",self.id,self.version,self.log_id,\
                self.provider,self.magic_num,self.reserved,self.body_len)

    def unpackage_header(self,head):
        '''�����յ���header,����dict,��������Ϣ��'''
        (self.id,self.version,self.log_id,self.provider,self.magic_num,self.reserved,self.body_len)=struct.unpack("!HHI16sIII",head)
        self.id = socket.ntohs(self.id)
        self.version = socket.ntohs(self.version)
        self.log_id = socket.ntohl(self.log_id)
        self.reserved = socket.ntohs(self.reserved)
        self.body_len = socket.ntohl(self.body_len)

        self.result = {}
        self.result["id"]=self.id
        self.result["version"]=self.version
        self.result["log_id"]=self.log_id
        self.result["provider"]=self.provider
        self.result["magic_num"]=self.magic_num
        self.result["reserved"]=self.reserved
        self.result["body_len"]=self.body_len
        return self.result
        
