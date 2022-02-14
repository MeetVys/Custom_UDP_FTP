from pprint import pprint
import socket 
import time
import multiprocessing as mp
from ctypes import c_bool

PORT = 3000
HOST = '127.0.0.5'
BUFFER_SIZE = 1024

client_socket_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
client_socket_send = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)        

class custom_packet :
    def __init__(self ,seq_number , data_size , syn , fin , data):
        self.seq_number = seq_number
        self.data_size = data_size
        self.syn = syn
        self.fin = fin
        self.data = data


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
            
    







base = 0 
next_seq = 0 
Window_Size = 10
def sender_thread_function () :
    file = open("rt1.txt","rb")
    while True :
        while next_seq < base + Window_Size :
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

