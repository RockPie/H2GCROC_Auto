# https://sentry.io/answers/print-colored-text-to-terminal-with-python/
import socket
import binascii
import time
import sys
import numpy as np 
import os

print ('argument list', sys.argv)
NUMARG = len(sys.argv)
if NUMARG == 2:
    scan = sys.argv[1]
else:
    scan = 0
    
print(scan)
time.sleep(5)
# ------------------------------------------------------------------------------------------------------------------------------------------------
# NN - ProtoBoard V1
# ------------------------------------------------------------------------------------------------------------------------------------------------
NumberOfASIC  = 2
ASIC_SELECT   = 3
SocketTimeOut = 5
NUMCH         = 72
INPUTDAC      = 64
NOINV         = 64
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Global Things
# ------------------------------------------------------------------------------------------------------------------------------------------------
HOST   ="10.1.2.207"
UDP_IP ="10.1.2.208"
PORT   =11000


# ------------------------------------------------------------------------------------------------------------------------------------------------
# Start...
# ------------------------------------------------------------------------------------------------------------------------------------------------
print("")
print("----------------------------------------------------------------------------------------------------------")
print(">>> Test Script for Pedestal Calibration             <<<")
print(">>>            004_PedestalScan.py                   <<<")
print("----------------------------------------------------------------------------------------------------------")
print("")

RED     = '\033[31m'
GREEN   = '\033[32m'
YELLOW  = '\033[33m'
BLUE    = '\033[34m'
MAGENTA = '\033[35m'
CYAN    = '\033[36m'
WHITE   = '\033[37m'
RESET   = '\033[0m' # called to return to standard terminal text color


# ------------------------------------------------------------------------------------------------------------------------------------------------
# Socket Init...
# ------------------------------------------------------------------------------------------------------------------------------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM , 0)
s.bind((HOST,PORT))
print(SocketTimeOut)
s.settimeout(SocketTimeOut) # Sets the socket to timeout after "SocketTimeOut" second of no activity
# ------------------------------------------------------------------------------------------------------------------------------------------------
# GetStatus, Check the communication
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Position     =[  00,  01,  02,  03,  04,  05,  06,  07,  08,  09,  10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  25,  26,  27,  28,  29,  30,  31,  32,  33,  34,  35,  36,  37,  38,  39 ]
MesGetStatus   =[0xa0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

s.sendto(bytes(MesGetStatus), (UDP_IP, PORT))
data, add = s.recvfrom(1024)

hex_string = binascii.hexlify(data).decode('utf-8')
hex_string2 = r" 0x" + r" 0x".join(hex_string[n : n+2] for n in range(0, len(hex_string), 2))

print("Get Status:")
print("Position:     00   01   02   03   04   05   06   07   08   09   10   11   12   13   14   15   16   17   18   19   20   21   22   23   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   39")
print("Status:    %s" % (hex_string2))
print("")
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Set the Generator Parameters
# ------------------------------------------------------------------------------------------------------------------------------------------------
print("Set Generator Parameters...")
# Position             =[  00,  01,  02,  03,  04,  05,  06,  07,  08,  09,  10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  25,  26,  27,  28,  29,  30,  31,  32,  33,  34,  35,  36,  37,  38,  39]
DAQ_SetGenerator       =[0xa0,0x00,0x07,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

DAQ_SetGenerator[3]  = ASIC_SELECT             # Data Collect Enable For All ASIC
DAQ_SetGenerator[4]  = 0                       # Trigger Data Collect Disable For All ASIC
DAQ_SetGenerator[7]  = 75                      # DAQ           FCMD: CMDL1A - 0b01001011
DAQ_SetGenerator[8]  = 75                      # Generator Pre FCMD: CMDL1A - 0b01001011
DAQ_SetGenerator[9]  = 75                      # Generator     FCMD: CMDL1A - 0b01001011
DAQ_SetGenerator[13] = 0                       # Generator PrePulse: 0 - Disable

DAQ_SetGenerator[14] = 0                       # Generator PreInterval 15:8
DAQ_SetGenerator[15] = 10                      # Generator PreInterval  7:0

DAQ_SetGenerator[16] = 0                       # Generator Nr. Of Cycle 31:24
DAQ_SetGenerator[17] = 0                       # Generator Nr. Of Cycle 23:16
DAQ_SetGenerator[18] = 1                       # Generator Nr. Of Cycle 15:8
DAQ_SetGenerator[19] = 0                       # Generator Nr. Of Cycle  7:0

DAQ_SetGenerator[20] = 0                       # Generator Interval 31:24
DAQ_SetGenerator[21] = 0                       # Generator Interval 23:16
DAQ_SetGenerator[22] = 0                       # Generator Interval 15:8
DAQ_SetGenerator[23] = 40                      # Generator Interval  7:0

DAQ_SetGenerator[24]  = 75                     # DAQ PUSH      FCMD: CMDL1A - 0b01001011   

for i in range (NumberOfASIC):
    DAQ_SetGenerator[0] = 160+i
    s.sendto(bytes(DAQ_SetGenerator), (UDP_IP, PORT))

time.sleep(0.5)
DAQ_StartGenerator     =[0xa0,0x00,0x09,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
DAQ_StartGenerator[5] = 1
DAQ_StartGenerator[6] = ASIC_SELECT
DAQ_StopGenerator      =[0xa0,0x00,0x09,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
print("")
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Start the run
# ------------------------------------------------------------------------------------------------------------------------------------------------
StartTheRun = [0xa0,0x00,0x11,0x00,0x00,0x01,0x05,0xa0,0x0b,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
for i in range (NumberOfASIC):
    StartTheRun[0] = 160+i
    s.sendto(bytes(StartTheRun), (UDP_IP, PORT))
time.sleep(0.5)
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Read All (NumberOfASIC) ASIC Top Registers...
# Sub-block address -> Top: 0d45
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Position     =[  00,  01,  02,  03,  04,  05,  06,  07,  08,  09,  10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  25,  26,  27,  28,  29,  30,  31,  32,  33,  34,  35,  36,  37,  38,  39 ]
MesReadI2CTop  =[0xa0,0x00,0x10,0x00,0x00,0x95,0x05,0xa0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0f,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

print("I2C Top register values:")
print("Position:     00   01   02   03   04   05   06   07   08   09   10   11   12   13   14   15   16   17   18   19   20   21   22   23   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   39")
for i in range (NumberOfASIC):
    MesReadI2CTop[0] = 160+i
    s.sendto(bytes(MesReadI2CTop), (UDP_IP, PORT))
    data, add = s.recvfrom(1024)

    hex_string = binascii.hexlify(data).decode('utf-8')
    hex_string2 = r" 0x" + r" 0x".join(hex_string[n : n+2] for n in range(0, len(hex_string), 2))
    print("ASIC%s Top: %s" % (i,hex_string2))
print("")

time.sleep(0.5)
# ------------------------------------------------------------------------------------------------------------------------------------------------
#     Read in all the channel I2C setup
# ------------------------------------------------------------------------------------------------------------------------------------------------
files = ["a0f0Channelwise.txt", "a1f0Channelwise.txt"]
Channel     = np.empty( (NumberOfASIC, NUMCH, 40) )
for asic in range(NumberOfASIC):
    fin = open( "config/" + files[asic] )
    Lines = fin.readlines()
    for line in Lines:
        first_word = line.split(" ",1)[0]
        i = 0
        if 'Channel' in first_word:
            for words in line.split():
                if i == 1: 
                    channelid = int(words)
                if i > 1: Channel[asic][channelid][i-2] = int(words, 16)
                i = i + 1
        # match first_word:
        #     case 'Channel':
        #         for words in line.split():
        #             if i == 1: 
        #                 channelid = int(words)
        #             if i > 1: Channel[asic][channelid][i-2] = int(words, 16)
        #             i = i + 1
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Start scanning different things
# ------------------------------------------------------------------------------------------------------------------------------------------------
WriteOneI2CRegister = [0xa0,0x00,0x11,0x00,0x00,0x01,0x06,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
ReadBackRegisters   = [0xa0,0x00,0x10,0x00,0x00,0x95,0x05,0xa0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0f,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
StartTheRun = [0xa0,0x00,0x11,0x00,0x00,0x01,0x05,0xa0,0x0b,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
StopTheRun = [0xa0,0x00,0x11,0x00,0x00,0x01,0x05,0xa0,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
# ------------------------------------------------------------------------------------------------------------------------------------------------
MesAdjustAll  =[0xa0,0x00,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
GetDebugData  =[0xa0,0x00,0x0C,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
# ------------------------------------------------------------------------------------------------------------------------------------------------
#Input dac scan for all channels
# ------------------------------------------------------------------------------------------------------------------------------------------------
if scan == "1": 
    directory = "000.InputDacScan"
    print(directory)
    IsDir = os.path.exists(str(directory))
    if IsDir:
        print("Already exist:  " + str(directory) );
    else: 
        os.mkdir( directory )
    for inputdac in range(INPUTDAC):
        #just in case stop the generator
        s.sendto(bytes(DAQ_StopGenerator), (UDP_IP, PORT))
        print("Inputdac scan: " + str(inputdac))
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Set the registers in each channel
        # ----------------------------------------------------------------------------------------------------------------------------------------
        for i in range (NumberOfASIC):
            for ichannel in range(72):
                #correct asic on correct board
                WriteOneI2CRegister[0] = int(Channel[i][ichannel][0]);
                WriteOneI2CRegister[1] = int(Channel[i][ichannel][1]);
                #single register
                WriteOneI2CRegister[6] = int(Channel[i][ichannel][6]);
                WriteOneI2CRegister[7] = int(Channel[i][ichannel][7]);
                WriteOneI2CRegister[8] = int(inputdac)
                s.sendto(bytes(WriteOneI2CRegister), (UDP_IP, PORT))
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Start the run
        # ----------------------------------------------------------------------------------------------------------------------------------------
        for i in range (NumberOfASIC):
            StartTheRun[0] = 160+i
            s.sendto(bytes(StartTheRun), (UDP_IP, PORT))
        time.sleep(0.5)
        print("Start The Run Sent!")
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Check Adjustment
        # ----------------------------------------------------------------------------------------------------------------------------------------
        adjust_ok = 0
        while adjust_ok == 0:
            for j in range (NumberOfASIC):
    
                GetDebugData[0] = 160+j
                s.sendto(bytes(GetDebugData), (UDP_IP, PORT))

                pack_ok = 0
                while pack_ok < 1 :

                    data, add = s.recvfrom(1024)
                    hex_string = binascii.hexlify(data).decode('utf-8')
                    hex_string2 = r" 0x" + r" 0x".join(hex_string[n : n+2] for n in range(0, len(hex_string), 2))
                
                    addr = hex_string2[0:5]

                    cmd = hex_string2[11:15]

                    daq0 = hex_string2[161:180]
                    daq0 = daq0.replace(" ", "")
                    daq0 = daq0.replace("0x", "")
    
                    daq1 = hex_string2[181:200]
                    daq1 = daq1.replace(" ", "")
                    daq1 = daq1.replace("0x", "")
    
                    pack_ok = 1
    
                    if (daq0 != "accccccc") or (daq1 != "accccccc"): 
                        daq0 =  RED + daq0 + RESET
                        daq1 =  RED + daq1 + RESET
                        adjust_ok = 0
                    else:
                        adjust_ok = 1
                print( "ASIC" + str(j) + " - " + str(daq0) + "  " + str(daq1))
                if adjust_ok == 0:
                    MesAdjustAll[15] = ASIC_SELECT
                    s.sendto(bytes(MesAdjustAll), (UDP_IP, PORT))    
                    time.sleep(0.5)

        print(adjust_ok)                    
        time.sleep(1)   
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Now start the generator
        # ----------------------------------------------------------------------------------------------------------------------------------------        
        s.sendto(bytes(DAQ_StartGenerator), (UDP_IP, PORT))
        print(DAQ_StartGenerator)
        print("Generator Start Sent!")

        PackCount = 0
        print("")
        print("Received Data:")
        print("")
        fp = open( str(directory) + "/InputDacScan" + str(f'{inputdac:02d}') + ".txt" ,"w")
        while True:
            try:
                data, add = s.recvfrom(8192)
                convert = bytes.hex(data)
                dataformat = [convert[i:i+2] for i in range(0, len(convert), 2)]
                newdata = str(' '.join(dataformat))
                payload = []
                header = []
                width = 120
                header.append(newdata[0:36])
                for i in range(36, len(newdata), width):
                    payload.append(newdata[i:i+width])
                    if payload[0][0] == "a":
                        fp.writelines(' '.join(payload) + '\n')
                    payload = []
                #print(header)
        
                PackCount = PackCount +1 
            except socket.timeout:
                print("")
                print("Break While! Socket Data Receive TimeOut is reached! (%s sec)" %(SocketTimeOut))
                break

        print("Received Packets: %s: " % (PackCount))
        print("")

        print("Generator Stop Sent!")
        s.sendto(bytes(DAQ_StopGenerator), (UDP_IP, PORT))
        fp.close()
        
        for i in range (NumberOfASIC):
            StopTheRun[0] = 160+i
            s.sendto(bytes(StopTheRun), (UDP_IP, PORT))
        time.sleep(0.5)
        print("Stop The Run Sent!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
#NoInv dac scan for all channels
# ------------------------------------------------------------------------------------------------------------------------------------------------
if scan == "2": 
    directory = "001.NoInvScan"
    print(directory)
    IsDir = os.path.exists(str(directory))
    if IsDir:
        print("Already exist:  " + str(directory) );
    else: 
        os.mkdir( directory )
    for no_inv in range(NOINV):
        #just in case stop the generator
        s.sendto(bytes(DAQ_StopGenerator), (UDP_IP, PORT))
        print("No Inv scan: " + str(no_inv))
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Set the registers in each channel
        # ----------------------------------------------------------------------------------------------------------------------------------------
        for i in range (NumberOfASIC):
            for ichannel in range(72):
                #correct asic on correct board
                WriteOneI2CRegister[0] = int(Channel[i][ichannel][0]);
                WriteOneI2CRegister[1] = int(Channel[i][ichannel][1]);
                #single register
                WriteOneI2CRegister[6] = int(Channel[i][ichannel][6]);
                WriteOneI2CRegister[7] = int(Channel[i][ichannel][7]) + 3;
                WriteOneI2CRegister[8] = int(4*no_inv)
                s.sendto(bytes(WriteOneI2CRegister), (UDP_IP, PORT))
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Start the run
        # ----------------------------------------------------------------------------------------------------------------------------------------
        for i in range (NumberOfASIC):
            StartTheRun[0] = 160+i
            s.sendto(bytes(StartTheRun), (UDP_IP, PORT))
        time.sleep(0.5)
        print("Start The Run Sent!")
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Check Adjustment
        # ----------------------------------------------------------------------------------------------------------------------------------------
        adjust_ok = 0
        while adjust_ok == 0:
            for j in range (NumberOfASIC):
    
                GetDebugData[0] = 160+j
                s.sendto(bytes(GetDebugData), (UDP_IP, PORT))

                pack_ok = 0
                while pack_ok < 1 :

                    data, add = s.recvfrom(1024)
                    hex_string = binascii.hexlify(data).decode('utf-8')
                    hex_string2 = r" 0x" + r" 0x".join(hex_string[n : n+2] for n in range(0, len(hex_string), 2))
                
                    addr = hex_string2[0:5]

                    cmd = hex_string2[11:15]

                    daq0 = hex_string2[161:180]
                    daq0 = daq0.replace(" ", "")
                    daq0 = daq0.replace("0x", "")
    
                    daq1 = hex_string2[181:200]
                    daq1 = daq1.replace(" ", "")
                    daq1 = daq1.replace("0x", "")
    
                    pack_ok = 1
    
                    if (daq0 != "accccccc") or (daq1 != "accccccc"): 
                        daq0 =  RED + daq0 + RESET
                        daq1 =  RED + daq1 + RESET
                        adjust_ok = 0
                    else:
                        adjust_ok = 1
                print( "ASIC" + str(j) + " - " + str(daq0) + "  " + str(daq1))
                if adjust_ok == 0:
                    MesAdjustAll[15] = ASIC_SELECT
                    s.sendto(bytes(MesAdjustAll), (UDP_IP, PORT))    
                    time.sleep(0.5)
        
        print(adjust_ok)
        time.sleep(1)
        # ----------------------------------------------------------------------------------------------------------------------------------------
        # Now start the generator
        # ----------------------------------------------------------------------------------------------------------------------------------------        
        s.sendto(bytes(DAQ_StartGenerator), (UDP_IP, PORT))
        print("Generator Start Sent!")

        PackCount = 0
        print("")
        print("Received Data:")
        print("")
        fp = open( str(directory) + "/NoInv" + str(f'{no_inv:02d}') + ".txt" ,"w")
        while True:
            try:
                data, add = s.recvfrom(8192)
                convert = bytes.hex(data)
                dataformat = [convert[i:i+2] for i in range(0, len(convert), 2)]
                newdata = str(' '.join(dataformat))
                payload = []
                header = []
                width = 120
                header.append(newdata[0:36])
                for i in range(36, len(newdata), width):
                    payload.append(newdata[i:i+width])
                    if payload[0][0] == "a":
                        fp.writelines(' '.join(payload) + '\n')
                    payload = []
                PackCount = PackCount +1 
            except socket.timeout:
                print("")
                print("Break While! Socket Data Receive TimeOut is reached! (%s sec)" %(SocketTimeOut))
                break

        print("Received Packets: %s: " % (PackCount))
        print("")

        print("Generator Stop Sent!")
        s.sendto(bytes(DAQ_StopGenerator), (UDP_IP, PORT))
        fp.close()
        
        for i in range (NumberOfASIC):
            StopTheRun[0] = 160+i
            s.sendto(bytes(StopTheRun), (UDP_IP, PORT))
        time.sleep(0.5)
        print("Stop The Run Sent!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Stop the run
# ------------------------------------------------------------------------------------------------------------------------------------------------
StopTheRun = [0xa0,0x00,0x11,0x00,0x00,0x01,0x05,0xa0,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
for i in range (NumberOfASIC):
    StopTheRun[0] = 160+i
    s.sendto(bytes(StartTheRun), (UDP_IP, PORT))
time.sleep(0.5)
print("Stop The Run Sent!")
# ------------------------------------------------------------------------------------------------------------------------------------------------
# Close
# ------------------------------------------------------------------------------------------------------------------------------------------------
s.close()



print("")
print(" >>> END <<<")
print("")

