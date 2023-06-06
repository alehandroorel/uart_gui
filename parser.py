from enum import Enum

LNS_SPEC_SIZE = 1
LNS_CMD_SIZE = 1
LNS_LENGTH_SIZE = 2
CRC_LEN = 1
HEADER_CTRL_LEN = LNS_SPEC_SIZE + LNS_CMD_SIZE + LNS_LENGTH_SIZE
HEADER_LEN = (1 + HEADER_CTRL_LEN)
STATUS_LEN = 1
SERVICE_LEN = HEADER_LEN + CRC_LEN
SERVICE_STATUS = HEADER_LEN + STATUS_LEN + CRC_LEN


class Stage(Enum):
    LNSBIN_HEAD_CHAR = 0
    LNSBIN_HEADER = 1
    LNSBIN_DATA = 2
    LNSBIN_CRC = 3


class Status(Enum):
    STATUS_OK = 0
    STATUS_NOT_ENOUGH_DATA = 1
    STATUS_NOT_A_CMD = 2
    STATUS_WRONG_CRC = 3
    STATUS_WRONG_DATA_FORMAT = 4
    STATUS_CONTINUE_UPDATING = 5


class Protocol():
    def __init__(self):
        self.curr_state = Stage.LNSBIN_HEADER
        self.cmd_spec = 0
        self.cmd_cmd = 0
        self.cmd_len = 0
        self.cmd_crc = 0
        self.cmd_data = ""
        self.is_first = True    #Тип страницы
        self.size_to_write = 0
        self.size_to_write_bytes = 0
        self.can_we_continue = True
        pass


# def ex_cmd(command, port_handle):
#     match prot.cmd_spec & 0xf0:
#         case


# rx_buff - string type
def parse_cmd(rx_buff, prot):
    if type(rx_buff) != type("rx_buff"):
        return Status.STATUS_WRONG_DATA_FORMAT
    state = Status.STATUS_OK
    exit_fl = False

    start = 0
    while not exit_fl:
        pos = rx_buff.find("\x24")
        if pos == -1:
            exit_fl = True
            state = Status.STATUS_NOT_ENOUGH_DATA
            prot.curr_state = Stage.LNSBIN_HEAD_CHAR

        mas_size = len(rx_buff)

        match prot.curr_state:
            case Stage.LNSBIN_HEAD_CHAR:
                start = rx_buff.find("\x24")
                if start == -1:
                    exit_fl = True
                    state = Status.STATUS_NOT_A_CMD
                    prot.curr_state = Stage.LNSBIN_HEAD_CHAR
                else:
                    prot.curr_state = Stage.LNSBIN_HEADER
                break
            case Stage.LNSBIN_HEADER:
                if mas_size - pos > HEADER_CTRL_LEN:
                    prot.cmd_spec = rx_buff[pos + 1]
                    prot.cmd_cmd = rx_buff[pos + 2]
                    prot.cmd_len = ord(rx_buff[pos + 3]) + (ord(rx_buff[pos + 4]) << 8)
                    prot.curr_state = Stage.LNSBIN_DATA
                else:
                    exit_fl = True
                    state = Status.STATUS_NOT_ENOUGH_DATA
                    prot.curr_state = Stage.LNSBIN_HEAD_CHAR
                break
            case Stage.LNSBIN_DATA:
                if mas_size - pos - HEADER_CTRL_LEN > prot.cmd_len + CRC_LEN:
                    prot.cmd_data = rx_buff[pos + 1 + HEADER_CTRL_LEN: pos + 1 + HEADER_CTRL_LEN + prot.cmd_len]
                    prot.curr_state = Stage.LNSBIN_CRC
                else:
                    exit_fl = True
                    state = Status.STATUS_NOT_ENOUGH_DATA
                    prot.curr_state = Stage.LNSBIN_HEAD_CHAR
                break
            case Stage.LNSBIN_CRC:
                for cmd_symb in rx_buff[pos:pos + 1 + HEADER_CTRL_LEN + prot.cmd_len]:
                    prot.cmd_crc = prot.cmd_crc ^ ord(cmd_symb)

                if prot.cmd_crc == ord(rx_buff[pos + HEADER_CTRL_LEN + prot.cmd_len + CRC_LEN]):
                    # Найти тут регулярку, что ок пришла страница или что ок прошилось + изменить поле прот
                    # temp_spec = int(prot.cmd_spec) & 0xF; // не работает

                    if ord(prot.cmd_cmd) == 3 and prot.cmd_len == 4 and ord(prot.cmd_spec) & 0xF:
                        temp_byte1 = ord(rx_buff[pos + HEADER_CTRL_LEN + 1])
                        temp_byte2 = ord(rx_buff[pos + HEADER_CTRL_LEN + 2])
                        temp_byte3 = ord(rx_buff[pos + HEADER_CTRL_LEN + 3])
                        temp_byte4 = ord(rx_buff[pos + HEADER_CTRL_LEN + 4])
                        if temp_byte1 == 0 and temp_byte2 == 0 and temp_byte3 == 0 and temp_byte4 == 0:
                            prot.can_we_continue = True
                            print("We could parse this cmd! Omgf, this is so exciting!!1")
                else:
                    exit_fl = True
                    state = Status.STATUS_WRONG_CRC
                    prot.curr_state = Stage.LNSBIN_HEAD_CHAR
            case _:
                exit_fl = True
                state = Status.STATUS_NOT_A_CMD
        prot.curr_state = Stage.LNSBIN_HEAD_CHAR

    return state


def prepare_protocol_unit(unit, cmd, spec, id):
    temp_len = len(unit)
    unit.insert(0, temp_len >> 8 & 0xFF)
    unit.insert(0, temp_len & 0xFF)
    unit.insert(0, cmd)
    unit.insert(0, (spec & 0xF) | (id & 0xF << 4) )
    unit.insert(0, 0x24)
    temp_crc = calc_crc_1(unit)
    unit.append(temp_crc)
    return unit


def calc_crc_1(data_mas):
    crc = 0
    for x in data_mas:
        crc = crc ^ x
    return crc
