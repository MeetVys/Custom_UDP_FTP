import socket
import time
import _thread 

PORT = 5507
REMOTE = '10.0.0.2'
LOCAL = '10.0.0.1'
BUFFER_SIZE = 4096
TIMEOUT = 1
count = 0 
start_time = time.time()
last_recv = time.time() 
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

control = True 
control1 = True 
control2 = True 
file = open("rcv1", "wb")

socket_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
socket_recv.bind((LOCAL, PORT))
socket_send = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
def time_out() :
    global control1 , control , last_recv 
    while control1: 
        time.sleep(3)
        if time.time() - last_recv > 10 :
            control1 = False
            control = False
            return
    return 

def recv():
    global recieved_data , base , REMOTE , PORT , count , start_time , end_time , control , control2 , control1 ,last_recv
    while control:
        rcvd_pckt , _ = socket_recv.recvfrom(BUFFER_SIZE)
        last_recv = time.time()
        message = rcvd_pckt.decode("latin-1").split(':')
        # print(message)
        rcv_seq = int(message[1])
        rcv_syn = int(message[5])
        rcv_fin = int(message[7])
        begin_data = len(message[0]) + len(message[1]) + len(message[2]) + len(message[3]) + len(message[4]) + len(message[5]) + len(message[6]) + len(message[7]) + len(message[8]) + 9
        data_rcv = rcvd_pckt[begin_data:]
        if rcv_syn == 1:
            if control2:
                control2 = False
                _thread.start_new_thread(time_out , ())
            print("Connection establishing")
            base = rcv_seq 
            start_time = time.time() 
            pk1 = custom_packet(rcv_seq , 1 , 0 )
            socket_send.sendto(pk1.get_string() , (REMOTE ,PORT ))
        elif rcv_fin == 1:
            control1 = False 
            control = False 
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
    global start_time , last_recv
    recv()
    print("Time taken" + str(last_recv - start_time))
    write_file()
    time.sleep(10)
    return

main_fn()
