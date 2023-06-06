 # Useful for further parsing
def output_list_of_bytes_as_string(list_of_bytes):
    temp = ""
    temp = temp.join(x.decode('Windows-1251') for x in list_of_bytes)
    return temp


def output_uint32_to_array(number):
    array = [0,  0, 0, 0]
    array[0] = (number >> 24) & 0xff;
    array[1] = (number >> 16) & 0xff;
    array[2] = (number >> 8) & 0xff;
    array[3] = number & 0xff;
    return array
