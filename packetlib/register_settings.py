import json

class RegisterSettings:
    def __init__(self, json_file_path):
        self.settings = {}
        self.load_settings(json_file_path)

    def load_settings(self, json_file_path):
        self.allowed_types = ['registers_top', 'registers_channel_wise', 'registers_global_analog', 'registers_reference_voltage','registers_master_tdc','registers_digital_half']
        try:
            with open(json_file_path, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            # throw an fatal error
            print('\033[31m' + 'Error: ' + '\033[0m' + 'File not found: ' + json_file_path)
            exit(1)
    
    def explain_reg_content(self, reg_content, reg_type_str):
        if reg_type_str not in self.allowed_types:
            print('\033[31m' + 'Error: ' + '\033[0m' + 'Invalid register type: ' + reg_type_str)
            return
        
        _target_reg_length = len(self.settings[reg_type_str][0].keys())
        if len(reg_content) > _target_reg_length:
            print('\033[31m' + 'Error: ' + '\033[0m' + 'Invalid register content length: ' + str(len(reg_content)))
            return

        for _reg_cnt in range(len(reg_content)):
            print('\033[34m' + "Reg " + str(_reg_cnt) + ": " + hex(reg_content[_reg_cnt]) + '\033[0m')
            for _bit_cnt in range(8):
                _bit_name = self.settings[reg_type_str][0]["register_"+str(_reg_cnt)][_bit_cnt]["name"]
                _bit_name = _bit_name.ljust(20)
                print('\033[0m' + "- Bit " + str(_bit_cnt) + " " + _bit_name + " " + str((reg_content[_reg_cnt] >> _bit_cnt) & 0x1) + '\033[0m')

    def available_reg_types(self):
        return self.allowed_types
    
    def get_default_reg_content(self, reg_type_str):
        if reg_type_str not in self.allowed_types:
            print('\033[31m' + 'Error: ' + '\033[0m' + 'Invalid register type: ' + reg_type_str)
            return
        
        _default_reg_content = []
        for _reg_cnt in range(len(self.settings[reg_type_str][0].keys())): # iterate over registers
            _value = 0x00
            for _bit_cnt in range(8):
                _value |= (self.settings[reg_type_str][0]["register_"+str(_reg_cnt)][_bit_cnt]["default_value"] << _bit_cnt)
            _default_reg_content.append(_value)
        return _default_reg_content