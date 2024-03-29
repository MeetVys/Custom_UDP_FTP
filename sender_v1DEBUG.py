from pickle import NONE
from pprint import pprint
from re import U
import socket
import time
import _thread
import os
import random

PORT = 6666
REMOTE = '127.0.0.1'
LOCAL = '127.0.0.2'
BUFFER_SIZE = 2048
PACKET_DATA_SIZE = 1024
WINDOW_SIZE = 200
TIMEOUT =  0.001
#list of size window , stores the packets that are currenty being transmitted
# seq_number -> packet
list_pack = dict()
#list of size window , stores the sequence number of packet being sent by the respective thread
# thread_number -> seq_number
list_seq = dict()
# list_ack = dict()
filename = "CS3543_100MB"
file = open( filename, "rb")
print ("file opened")
file_sent = False
filesize = os.path.getsize(filename)

count = 0 

#lock for send socket as there are multiple sending threads
socket_lock = _thread.allocate_lock()

# conn_est timer
control1 = True 

# sending timer
control2 = True

# finish timer 
control3 = True

base = random.getrandbits(14)
activated_sending_threads = 0

socket_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
socket_recv.bind((LOCAL , PORT))
socket_send = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

class custom_packet :
    def __init__(self ,seq_number , syn , fin , data , data_size ):
        self.seq_number = seq_number
        self.data_size = data_size
        self.syn = syn
        self.fin = fin
        self.data = data
    def get_string(self):
        if self.data == None:
            temp = ("seq:"+str(self.seq_number)+":size:"+str(self.data_size)+":syn:"+str(self.syn)+":fin:"+str(self.fin)+":data:").encode() 
        else :   
            temp = ("seq:"+str(self.seq_number)+":size:"+str(self.data_size)+":syn:"+str(self.syn)+":fin:"+str(self.fin)+":data:").encode() + self.data
        return temp
    def get_size(self):
        temp = self.get_string()
        return len(temp)


def get_packet_special(SYN , FIN , seq_number) :
    pckt = custom_packet(seq_number , SYN ,FIN , None , 0 )
    return pckt

def get_packet_default (seq_number):
    global file , control2 , activated_sending_threads , count 
    # print("get default runiing ")
    # print("tryn data read")
    data_read = file.read(PACKET_DATA_SIZE)
    
    if not data_read : 
        print("File exhausted")
        activated_sending_threads -= 1
        control2 = False 
        return None
    else:
        count += 1
        # print(count)
        pckt = custom_packet(seq_number , 0, 0  , data_read, PACKET_DATA_SIZE )
        # print(data_read)
        return pckt

def conn_est():
    global control1 , socket_send , base , REMOTE , PORT
    p = get_packet_special(1,0,base)
    base += 1
    print("est packet sent")
    # print(p.get_string())
    socket_send.sendto(p.get_string() , (REMOTE,PORT))
    start_time = time.time()
    _thread.start_new_thread(conn_est_timer , (p , start_time ,))
    while True:
        recv_packet , _  = socket_recv.recvfrom(BUFFER_SIZE)
        print("est packet recieved")
        message = recv_packet.decode()
        # print(message)
        message = message.split(':')
        rcv_seq = int(message[1])
        rcv_syn = int(message[3])
        rcv_fin = int(message[5])
        if rcv_syn ==1 :
            control1 = False
            return True
        else:
            control1 = False
            return False

def conn_est_timer(pckt, start_time):
    global control1 , socket_send , TIMEOUT , REMOTE , PORT
    while control1:
        
        if time.time() - start_time > TIMEOUT:
            socket_send.sendto( pckt.get_string() , (REMOTE,PORT))
            start_time = time.time()
            print("connection established timer debug")
    print(control1)
    print("exting timer conn")
    return


def sender(id) :
    global list_pack , list_seq, control2 , socket_lock , socket_send
    while control2:
        while list_pack[list_seq[id]] is not None:
            socket_lock.acquire()
            # print(str(list_seq[id]) + "being resent")
            socket_send.sendto ( list_pack[list_seq[id]].get_string(), (REMOTE,PORT) )
            socket_lock.release()
            time.sleep(TIMEOUT)
    print("thead ended" + str(id))
    return

def  sender_main() :
    global base , WINDOW_SIZE , activated_sending_threads , list_pack , list_seq
    for i in range(WINDOW_SIZE):
        print("get packet"+ str(i))
        pckt = get_packet_default(base)
        # print(pckt.get_string() )
        activated_sending_threads += 1
        list_pack[base] = pckt
        list_seq[i+1] = base
        _thread.start_new_thread(sender, (i+1,))
        base += 1
        # print(list_pack)
        # print(list_seq)
    return

def recv():
    global list_pack , list_seq, control2 , base  ,  activated_sending_threads
    print("Recv started")
    while True:
        recv_packet , _  = socket_recv.recvfrom(BUFFER_SIZE)
        message = recv_packet.decode()
        # print(message)
        message = message.split(':')
        rcv_seq = int(message[1])
        rcv_syn = int(message[3])
        rcv_fin = int(message[5])
        if rcv_seq in list(list_seq.values()):
            update_thread_id = list(list_seq.values()).index(rcv_seq)
            update_thread_id += 1
            # print("Thread update_thread_id" + str(update_thread_id))
            if control2 == False:
                # print("for 1 thread do not execute")
                list_pack[rcv_seq]= None
                activated_sending_threads -= 1
                # print("Activated threads:" + str(activated_sending_threads))
            else:
                # print("getting new packet")
                new_pckt = get_packet_default(base)
                # if new_pckt is not None:
                #     print(new_pckt.get_string())
                # print("Activated threads:" + str(activated_sending_threads))
                list_pack[base] = new_pckt
                list_seq[update_thread_id] = base
                base += 1
        if activated_sending_threads == 0 :
            print("Conn_end")
            return

def conn_end():
    global control3 , socket_send , base  , REMOTE , PORT 
    p = get_packet_special(0,1,base)
    base += 1
    socket_send.sendto( p.get_string() , (REMOTE,PORT))
    start_time = time.time()
    _thread.start_new_thread(conn_end_timer , (p , start_time ,))
    while True:
        recv_packet , _  = socket_recv.recvfrom(BUFFER_SIZE)
        message = recv_packet.decode()
        # print(message)
        message = message.split(':')
        rcv_seq = int(message[1])
        rcv_syn = int(message[3])
        rcv_fin = int(message[5])
        if rcv_fin ==1 :
            control3 = False
            return True

def conn_end_timer(p , start_time):
    global control3 , socket_send , TIMEOUT
    while control3:
        if time.time()- start_time > TIMEOUT:
            socket_send.sendto( p.get_string() , (REMOTE,PORT))
            start_time = time.time()
    return

def main_fn () :
    global count 
    print("Main called estb")
    established = conn_est()
    if( established == True):
        pprint("Connection established with reciever")
    else :
        pprint("Unable to connect with the reciever")
        return
    send_time_start = time.time()
    sender_main()
    recv()
    send_time_end = time.time()
    time.sleep(1)
    if activated_sending_threads == 0:
        conn_end()
    else:
        pprint("Incorrect connection termination")
    time_taken = send_time_end - send_time_start
    pprint(time_taken)
    print(count)
    return

main_fn()
