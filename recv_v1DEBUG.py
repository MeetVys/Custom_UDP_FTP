from pprint import pprint
from pydoc import cli
import socket
import time
import _thread
import os
from traceback import print_list

PORT = 6666
REMOTE = '127.0.0.2'
LOCAL = '127.0.0.1'
BUFFER_SIZE = 2048
PACKET_DATA_SIZE = 1024
WINDOW_SIZE = 1
TIMEOUT = 1
count = 0 
class custom_packet :
    def __init__(self ,seq_number , syn , fin ):
        self.seq_number = seq_number
        self.syn = syn
        self.fin = fin
    def get_string(self):
        temp = ("seq:"+str(self.seq_number)+":syn:"+str(self.syn)+":fin:"+str(self.fin)).encode()
        return temp
    def get_size(self):
        temp = ("seq:"+str(self.seq_number)+":syn:"+str(self.syn)+":fin:"+str(self.fin)).encode()
        return len(temp)

#stores all the recieved packets's data 
recieved_data = dict() 
base = 0 

file = open("rcv1", "wb")


socket_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
socket_recv.bind((LOCAL, PORT))
socket_send = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

def recv():
    global recieved_data , base , REMOTE , PORT , count 
    while True:
        rcvd_pckt , _ = socket_recv.recvfrom(BUFFER_SIZE)
        message = rcvd_pckt.decode("latin-1").split(':')
        # print(message)
        rcv_seq = int(message[1])
        rcv_syn = int(message[5])
        rcv_fin = int(message[7])
        begin_data = len(message[0]) + len(message[1]) + len(message[2]) + len(message[3]) + len(message[4]) + len(message[5]) + len(message[6]) + len(message[7]) + len(message[8]) + 9
        data_rcv = rcvd_pckt[begin_data:]
        if rcv_syn == 1:
            print("Connection establishing")
            base = rcv_seq 
            pk1 = custom_packet(rcv_seq , 1 , 0 )
            socket_send.sendto(pk1.get_string() , (REMOTE ,PORT ))
        elif rcv_fin == 1:
            print("connection ending")
            pk2 = custom_packet(rcv_seq , 0 , 1)
            socket_send.sendto(pk2.get_string() , (REMOTE ,PORT ))
            return 
        else:
            # print("data_recieved")
            pk3 = custom_packet(rcv_seq , 0, 0)
            socket_send.sendto(pk3.get_string() , (REMOTE, PORT ))
            if (rcv_seq - base) not in recieved_data.keys() :
                count += 1 
                recieved_data[rcv_seq - base] = data_rcv 
            # print(data_rcv)

def write_file():
    global file 
    for i in sorted(recieved_data) :
        file.write(recieved_data[i])
    return 

def main_fn():
    recv()
    print(count)
    write_file()

    return

main_fn()