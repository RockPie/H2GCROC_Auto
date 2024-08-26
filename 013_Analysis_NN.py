import struct
import numpy as np 
import sys
import matplotlib.pyplot as plt
import math
import time

print ('argument list', sys.argv)
NUMARG = len(sys.argv)
if NUMARG == 3:
    inputfile = sys.argv[1]
    outputfile = sys.argv[2]
else:
    inputfile = "RunTest.txt"
    outputfile = "Pedestal.txt"

f = open(inputfile, "r")
#f = open("NewTest.txt", "r")

Lines = f.readlines()

event = 0;
prefpgacounter = -1;

asics = 2
LinePerHalf = 5
ChannelPerHalf = 36
##################################################################
# This decodes the 32-bit integer to ADC, ADCm1, TOA and TOT
##################################################################
def decodedata( datain ):
    tc = datain >> 31;
    tp = (datain >> 30) & 0x01;
    m0 = ( (datain>>20) & 0x03FF);
    m1 = ( (datain>>10) & 0x03FF);
    m2 = (datain & 0x03FF);
    adc = 0;
    adcm1 = 0;
    toa = 0;
    tot = 0;
    if tc == 0 and tp == 0:
        adcm1 = m0
        adc = m1
        toa = m2
    if tc == 0 and tp == 1:
        adcm1 = m0
        adc = m1
        toa = m2
    if tc == 1 and tp == 0:
        adcm1 = m0
        tot = m1
        toa = m2
    if tc == 1 and tp == 1:
        adc = m0
        tot = m1
        toa = m2
    return tc, tp, adcm1, adc, toa, tot
    
##################################################################
# Collect one event of 32-bit words from all ASICs
##################################################################    
class FullEventConstruct:
    iDchip = 0;
    iDhalf = 0;
    iDline = [None]
    TimeStampFPGA = [None]
    header = 0;
    crc32 = 0
    
FullEventConstruct.iDchip = []
FullEventConstruct.iDhalf = []
FullEventConstruct.iDline = []
FullEventConstruct.TimeStampFPGA = []
FullEventConstruct.header = []
FullEventConstruct.crc32 = []
##################################################################
# Decoded full event with all ASICs
##################################################################
chann, asics = (72, 2) 
channel = np.empty( (asics, chann) )
##################################################################
# Read all data in
##################################################################
list = []

for line in Lines:
    num = 0;
    chipID = line.split()[0]
    lineID = line.split()[2]
    lineNum = line.split()[3]
    #print( str(chipID) + "  " + str(lineID) + "  " + str(lineNum) + "   ", end = "  "),
    FullEventConstruct.iDchip.append( int(chipID, 16) )
    FullEventConstruct.iDhalf.append( int(lineID, 16) )
    FullEventConstruct.iDline.append( int(lineNum, 16) )
    class EventReco:
        channels = np.empty( (asics, chann) )
    
    asicn = -1
    if int(chipID, 16) == 160:
        asicn = 0
    if int(chipID, 16) == 161:
        asicn = 1        
    
    if lineID == "24" : 
        fpgacounter = line.split()[4]+line.split()[5]+line.split()[6]+line.split()[7]
        #print(fpgacounter)
        FullEventConstruct.TimeStampFPGA.append(int(fpgacounter, 16))
        
        if lineNum == "00":
            header = line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11];
            cmn = line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15];
            channel[asicn][0] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][1] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][2] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][3] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][4] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][5] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
            FullEventConstruct.header.append(header)
        elif lineNum == "01":
            channel[asicn][6] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][7] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][8] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][9] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][10] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][11] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][12] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][13] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "02":
            channel[asicn][14] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][15] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][16] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            calib = line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23];
            channel[asicn][17] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][18] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][19] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][20] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "03":
            channel[asicn][21] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][22] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][23] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][24] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][25] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][26] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][27] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][28] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "04":
            channel[asicn][29] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][30] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][31] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][32] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][33] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][34] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][35] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            crc32 = line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39];
            FullEventConstruct.crc32.append(crc32)
    if lineID == "25" : 
        fpgacounter = line.split()[4]+line.split()[5]+line.split()[6]+line.split()[7]
        #print(fpgacounter)
        FullEventConstruct.TimeStampFPGA.append(int(fpgacounter, 16))
        
        if lineNum == "00":
            header = line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11];
            cmn = line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15];
            channel[asicn][36] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][37] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][38] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][39] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][40] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][41] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
            FullEventConstruct.header.append(header)
        elif lineNum == "01":
            channel[asicn][42] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][43] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][44] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][45] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][46] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][47] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][48] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][49] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "02":
            channel[asicn][50] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][51] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][52] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            calib = line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23];
            channel[asicn][53] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][54] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][55] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][56] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "03":
            channel[asicn][57] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][58] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][59] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][60] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][61] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][62] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][63] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            channel[asicn][64] = int(line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39], 16);
        elif lineNum == "04":
            channel[asicn][65] = int(line.split()[8] + line.split()[9] + line.split()[10] + line.split()[11], 16);
            channel[asicn][66] = int(line.split()[12] + line.split()[13] + line.split()[14] + line.split()[15], 16);
            channel[asicn][67] = int(line.split()[16] + line.split()[17] + line.split()[18] + line.split()[19], 16);
            channel[asicn][68] = int(line.split()[20] + line.split()[21] + line.split()[22] + line.split()[23], 16);
            channel[asicn][69] = int(line.split()[24] + line.split()[25] + line.split()[26] + line.split()[27], 16);
            channel[asicn][70] = int(line.split()[28] + line.split()[29] + line.split()[30] + line.split()[31], 16);
            channel[asicn][71] = int(line.split()[32] + line.split()[33] + line.split()[34] + line.split()[35], 16);
            crc32 = line.split()[36] + line.split()[37] + line.split()[38] + line.split()[39];                
            FullEventConstruct.crc32.append(crc32)
    
    if len(FullEventConstruct.TimeStampFPGA) == 20:
        #make some checks that the event data is all good

        #fill the object list with the channels
        for asic in range(asics):
            for ch in range(chann):
                EventReco.channels[asic][ch] = channel[asic][ch]
        list.append(EventReco())

        event = event + 1
        FullEventConstruct.iDchip = []
        FullEventConstruct.iDhalf = []
        FullEventConstruct.iDline = []
        FullEventConstruct.TimeStampFPGA = []
        FullEventConstruct.header = []
        FullEventConstruct.crc32 = []    
          
print(event)
#calculate the average for pedestal ADC's
channum = np.empty( (asics, chann) )
average = np.empty( (asics, chann) )
rmsaver = np.empty( (asics, chann) )
for asic in range(asics):
    for ch in range(chann):
        average[asic][ch] = 0;
        rmsaver[asic][ch] = 0;
#just making sure there are zeroed out

hist_2d_0 = np.zeros((1024, 72))
hist_2d_1 = np.zeros((1024, 72))

for obj in list:
    for asic in range(asics):
        for ch in range(chann):
            tc, tp, adcm1, adc, toa, tot = decodedata(int(obj.channels[asic][ch]))
            #if asic==0: print( str(tc) + "  " + str(tp) + "  " + str(adcm1) + "  " + str(adc) + "  " + str(toa) + "  " + str(tot))
            if asic==0: hist_2d_0[adc][ch] += 1
            if asic==1: hist_2d_1[adc][ch] += 1

fped = open(outputfile, "w")

for i in range(1024):
    for ch in range(chann):
        #print("Bin ({}, {}): {}".format(i, j, hist_2d_0[i, j]))
        average[0][ch] = average[0][ch] + i*hist_2d_0[i, ch]
        rmsaver[0][ch] = math.sqrt( rmsaver[0][ch] + (i*hist_2d_0[i, ch])*(i*hist_2d_0[i, ch]) )
        channum[0][ch] = channum[0][ch] + hist_2d_0[i, ch]
for i in range(1024):
    for ch in range(chann):
        #print("Bin ({}, {}): {}".format(i, j, hist_2d_1[i, j]))
        average[1][ch] = average[1][ch] + i*hist_2d_1[i, ch]
        rmsaver[1][ch] = math.sqrt( rmsaver[1][ch] + (i*hist_2d_1[i, ch])*(i*hist_2d_1[i, ch]) )
        channum[1][ch] = channum[1][ch] + hist_2d_1[i, ch]

for asic in range(asics):
    for ch in range(chann):
        average[asic][ch] = average[asic][ch]/channum[asic][ch]
        rmsaver[asic][ch] = math.sqrt(rmsaver[0][0]/channum[0][0])
        print( str(asic) + "   " + str(ch) + "  " + str(average[asic][ch]) + "   " + str(rmsaver[asic][ch]))
        fped.writelines( str(asic) + "   " + str(ch) + "  " + str(average[asic][ch]) + "   " + str(rmsaver[asic][ch]) + "\n"  )

max_count = max(np.max(hist_2d_0), np.max(hist_2d_1))/2
fig, axs = plt.subplots(2, 1, figsize=(8, 6))
fig.set_facecolor('white')
# Plot the first histogram
axs[0].imshow(hist_2d_0, cmap='Greys', origin='lower', aspect='auto', vmin=0, vmax=max_count)
axs[0].set_title('Asic 0')
axs[0].set_xlabel('Channel')
axs[0].set_ylabel('ADC')
axs[0].set_xticks([])
axs[0].set_yticks([])

# Plot the second histogram
axs[1].imshow(hist_2d_1, cmap='Greys', origin='lower', aspect='auto', vmin=0, vmax=max_count)
axs[1].set_title('Asic 1')
axs[1].set_xlabel('Channel')
axs[1].set_ylabel('ADC')
axs[1].set_xticks([])
axs[1].set_yticks([])

# Adjust layout
plt.tight_layout()
# Show the plot
#plt.show()
plt.savefig('Pedestals.pdf')
