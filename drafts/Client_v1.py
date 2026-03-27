from pprint import pprint
from pydoc import cli
import socket
from struct import pack 
import time
import _thread
import os

PORT = 3000
HOST = '127.0.0.5'
BUFFER_SIZE = 1024
PACKET_DATA_SIZE = 1024
WINDOW_SIZE = 10

#list of size window , stores the packets that are currenty being transmitted 
# seq_number -> packet
list_pack = dict()
#list of size window , stores the sequence number of packet being sent by the respective thread
# thread_number -> seq_number
list_seq = dict() 
list_ack = dict()

file = open("m1.txt", "rb")
file_sent = False 
base = 0 
next_seq = 0 
socket_lock = _thread.allocate_lock() 
control = True 

client_socket_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_socket_send = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)        

class custom_packet :
    def __init__(self ,seq_number , data_size , syn , fin , data):
        self.seq_number = seq_number
        self.data_size = data_size
        self.syn = syn
        self.fin = fin
        self.data = data
    def get_string(self):
        temp = ("seq:"+str(self.seq_number)+"size:"+str(self.data_size)+"syn:"+str(self.syn)+"fin:"+str(self.fin)+"data:").encode() + self.data
        return temp

def get_packet (SYN, FIN, seq_number):
    global file 
    packet_obj  = custom_packet()
    packet_obj.data_size = PACKET_DATA_SIZE
    packet_obj.seq_number = seq_number
    packet_obj.syn = SYN 
    packet_obj.fin = FIN 
    packet_obj.data = file.read(PACKET_DATA_SIZE)
    list_seq[seq_number%WINDOW_SIZE] = packet_obj

    return packet_obj
    
    



def conn_est_timer(p , start_time): 
    while established != True:
        if time.time - start_time > TIMEOUT:
            client_socket_send.sendto('hello UDP server from client'.encode(), (HOST,PORT))
            start_time = time.time()
    return 
        
def conn_est():
    established = mp.Value(c_bool , False)
    p = make_packet()
    client_socket_send.sendto('hello UDP server from client'.encode(), (HOST,PORT))
    start_time = time.time()
    p1 = mp.Process(conn_est_timer , (p , start_time, ))
    p1.start()
    while True:
        recv_packet = client_socket_recv.recvfrom(BUFFER_SIZE)

        if packet.correct_conn():
            established = True 
            p1.join()
            break
        else:
            print("Failed")
            
    
def sender(id) : 
    global list_pack , list_seq, control 
    while control:

        while list_packet(list_seq(id)) Null:
            send_lo
            send( packet(list_seq(id)))
            sleep()


def  sender_main() :
    for i in range(WINDOW_SIZE):
        pckt = get_packet(0,0,i+1)
        list_pack.add(i+1 , pckt)
        list_seq( i+1 , i+1)
        _thread.start_new_thread(sender, (i+1))
    
def recv():
    sender_main()
    while True
        rcvd_pckt , _ = client_socket_recv.recvfrom(BUFFER_SIZE)
    decode() 
    seq() 
    if seq in list_seq
        find thread corresp to seq 
        add packet to packet_list
        list_seq(thread_id) <- update 
        ++base
    

    for in list
        join

            # send packet
            pckt = get_packet(0,0,next_seq)
            pckt = pckt.get_string
            client_socket_send.sendto(pckt,(HOST,PORT))
            list_ack[next_seq%WINDOW_SIZE] = 0 
            # call thread timer 






            #  Make packet and store it in the temp
            # send packet
            # make thread which retransmits if timeout


def main_fn () :
    #  Call Sender thread
    while True :
        recv_packet = client_socket_recv.recvfrom(BUFFER_SIZE)
        # Check if packet is corrupted or not
        # if not corrupted then
        # 

