from itertools import groupby

def extract_raw_payloads(data):
    # Constant values
    HEADER_SIZE = 12
    PAYLOAD_SIZE = 40
    PAYLOAD_START_OPTIONS   = range(0xA0, 0xA3)  # 0xA0 to 0xA7
    SECOND_BYTE_OPTIONS     = range(0x00, 0x08)   # 0x00 to 0x07
    THIRD_BYTE_OPTIONS      = [0x24, 0x25]
    FOURTH_BYTE_OPTIONS     = range(0x00, 0x05)
    
    # Initialize a list to store payloads
    payloads = []

    # Skip the header to get to the payload
    payload_data = data[HEADER_SIZE:]

    # Check each possible start index in the payload data
    for i in range(len(payload_data) - PAYLOAD_SIZE + 1):
        # Check for the criteria
        if payload_data[i] in PAYLOAD_START_OPTIONS and \
           payload_data[i+1] in SECOND_BYTE_OPTIONS and \
           payload_data[i+2] in THIRD_BYTE_OPTIONS and \
           payload_data[i+3] in FOURTH_BYTE_OPTIONS:
            # Extract the 40-byte payload
            payload = payload_data[i:i + PAYLOAD_SIZE]
            payloads.append(payload)

    return payloads

def sort_and_group_40bytes(data):
    # Helper function to get the key for sorting and grouping
    def get_key(item):
        return item[0:3], item[4:7]  # (bytes 1-3, bytes 5-7)

    # Sort the data first; necessary for groupby to work correctly
    data_sorted = sorted(data, key=lambda x: (x[0:3], x[4:7], x[3]))

    # Use groupby to group data by bytes 1-3 and 5-7
    grouped_data = []
    for ((bytes_1_3, bytes_5_7), items) in groupby(data_sorted, key=get_key):
        sub_group = sorted(list(items), key=lambda x: x[3])  # Ensure fourth byte is sorted from 0x00 to 0x03
        grouped_data.append(sub_group)

    return grouped_data

def assemble_data_from_40bytes(group, verbose=False):
    # put the group of 5 40-byte data into a single 200-byte data
    data = bytearray()
    for i in range(len(group)):
        data += group[i]
    if len(data) != 200:
        if verbose:
            print('\033[33m' + "Error: Data length is not 200 bytes" + '\033[0m')
        return None
    _header      = data[0]
    _fpga_addr   = data[1]
    _packet_type = data[2]
    _timestamp   = data[4:7]
    _extraced_160_bytes  = data[8:40]
    _extraced_160_bytes += data[48:80]
    _extraced_160_bytes += data[88:120]
    _extraced_160_bytes += data[128:160]
    _extraced_160_bytes += data[168:200]
    if verbose:
        print('\033[34m' + "Header: " + hex(_header) + '\033[0m')
        print('\033[34m' + "FPGA Address: " + hex(_fpga_addr) + '\033[0m')
        print('\033[34m' + "Packet Type: " + hex(_packet_type) + '\033[0m')
        print('\033[34m' + "Timestamp: " + hex(_timestamp[0]) + hex(_timestamp[1]) + hex(_timestamp[2]) + '\033[0m')
        print('\033[34m' + "Data: " + '\033[0m')
        for i in range(0, 160, 16):
            print(' '.join([f"{x:02x}" for x in _extraced_160_bytes[i:i+16]]))
    return {
        "_header": _header,
        "_fpga_addr": _fpga_addr,
        "_packet_type": _packet_type,
        "_timestamp": _timestamp,
        "_extraced_160_bytes": _extraced_160_bytes
    }

def check_event_fragment(candidate_packet_lines):
    if len(candidate_packet_lines) != 5:
        return False, None
    else:
        return True, candidate_packet_lines
    
def extract_values(bytes_input, verbose=False):
    if len(bytes_input) != 160:
        if verbose:
            print('\033[33m' + "Error: Data length is not 160 bytes" + '\033[0m')
        return None
    _DaqH = bytes_input[0:4]
    _extracted_values = []
    for i in range(4, 152, 4):
        _value = int.from_bytes(bytes_input[i:i+4], byteorder='big', signed=False)
        if verbose:
            print('\033[34m' + "Value: " + hex(_value) + '\033[0m')
        _val0  = (_value >> 20) & 0x3FF
        _val1  = (_value >> 10) & 0x3FF
        _val2  = (_value >>  0) & 0x3FF
        _tctp  = (_value >> 30) & 0x3
        # if (i//4 == 7) and (_val0 > 400):
        #     # print the byte_input
        #     print('\033[33m' + "byte_input: " + ' '.join([f"{x:02x}" for x in bytes_input]) + '\033[0m')

        _extracted_values.append([_tctp, _val0, _val1, _val2])
    if verbose:
        print('\033[34m' + "DaqH: " + ' '.join([f"{x:02x}" for x in _DaqH]) + '\033[0m')
        print('\033[34m' + "Extracted Values: " + '\033[0m')
        for i in range(len(_extracted_values)):
            print(' '.join([f"{x:04x}" for x in _extracted_values[i]]))
    return {
        "_DaqH": _DaqH,
        "_extracted_values": _extracted_values
    }

def DaqH_get_H1(_daqh):
    if len(_daqh) != 4:
        return None
    # Ensure the element is treated as an integer
    value = int(_daqh[-1])
    return (value & 0x40) >> 6

def DaqH_get_H2(_daqh):
    if len(_daqh) != 4:
        return None
    # Ensure the element is treated as an integer
    value = int(_daqh[-1])
    return (value & 0x20) >> 5

def DaqH_get_H3(_daqh):
    if len(_daqh) != 4:
        return None
    # Ensure the element is treated as an integer
    value = int(_daqh[-1])
    return (value & 0x10) >> 4