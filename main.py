from tkinter import *
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
import serial
import serial.tools.list_ports
import parser
import custom_output as converter
import math
import numpy as np

PAGE_SIZE = 256  # bytes


# Scan available COM ports
# TODO: write it to groupbox
def click_btn_scan(event):
    ports = serial.tools.list_ports.comports()
    for p in ports:
        write_to_editor(p.device + '\n')
        # print(p.device)
    write_to_editor(str(len(ports)) + ' ports found\n')
    # print(len(ports), 'ports found')
    combo_ports["values"] = ports
    combo_ports.set(ports[0])


def click_btn_con(event):
    port = combo_ports.get()
    com = port[0:port.find(" ")]
    if (ser.is_open == True) or (ser.port != com):
        ser.close()

    if port != None and ser.port != com:
        write_to_editor(port + '\n')
        # print(port)
        # print(com)
        ser.baudrate = 115200
        ser.port = com
        ser.open()
        # ser.write(b'hello')
        # print(ser.is_open)


def write_to_editor(text):
    editor.insert(END, text)
    editor.see('end')


def click_btn_upd(event):
    filename = filedialog.askopenfilename(initialdir="/", title="Select a File", filetypes=(("Bin files",
                                                      "*.bin*"), ("all files", "*.*")))
    print(filename)
    f = open(filename, mode="rb")
    text = bytearray(f.read())
    print(text)
    print(len(text))
    main_prot.size_to_write = math.ceil((len(text) + 12) / PAGE_SIZE)
    print(main_prot.size_to_write)
    main_prot.is_first = True
    main_prot.size_to_write_bytes = len(text) + 12
    firmware_magic = bytearray(converter.output_uint32_to_array(np.uint32(0xf0a5c8b3)))
    temp_crc32 = np.uint32(calc_crc32(text))
    real_crc32 = ((temp_crc32 & 0xFF) << 24) | ((temp_crc32 & 0xFF00) << 8) | ((temp_crc32 & 0xFF0000) >> 8) \
        | ((temp_crc32 & 0xFF000000) >> 24)
    firmware_crc = bytearray(converter.output_uint32_to_array(real_crc32))
    firmware_size = bytearray(converter.output_uint32_to_array(np.uint32(len(text))))
    print(firmware_magic)
    print(firmware_crc)
    print(firmware_size)
    sub_text = firmware_magic + firmware_size + firmware_crc + text
    print(len(sub_text))
    send_firmware(main_prot, sub_text)


def send_firmware(protocol, firmware):
    j = main_prot.size_to_write
    temp_fw = []
    crc = 0
    mas = []
    temp_rx = []
    stringlist = ""
    print(type(firmware))
    # firmware.insert(0, firmware_size)
    # firmware.insert(0, firmware_magic)
    while j > 0:
        if protocol.can_we_continue is True:
            if main_prot.is_first == True:
                main_prot.is_first = False
                # temp_fw = firmware[PAGE_SIZE * (main_prot.size_to_write - j) : PAGE_SIZE * (main_prot.size_to_write - j + 1)]
                for i in range(PAGE_SIZE):
                    temp_fw.insert(0, int(firmware[(main_prot.size_to_write - j) * PAGE_SIZE + PAGE_SIZE - i - 1]))
                temp_fw.append(0x45)
                temp_fw.append(0x6e)
                temp_fw.append(0x64)
                crc = calc_crc(temp_fw)
            elif j == 1:
                # temp_fw = firmware[PAGE_SIZE * (main_prot.size_to_write - j): END]
                temp_size = main_prot.size_to_write_bytes - PAGE_SIZE * (main_prot.size_to_write -1)
                for i in range(temp_size):
                    temp_fw.insert(0, int(firmware[(main_prot.size_to_write - j) * PAGE_SIZE + temp_size - i - 1]))
                temp_fw.append(0x45)
                crc = calc_crc(temp_fw)
                temp_fw.insert(0, crc)
                if temp_size == PAGE_SIZE:
                    temp_fw.insert(0, 0)
                    temp_fw.insert(0, 1)
                else:
                    temp_fw.insert(0, temp_size)
                    temp_fw.insert(0, 0)
                temp_fw.insert(0, 0x55)

                temp_fw.append(0x6e)
                temp_fw.append(0x64)
            else:
                # temp_fw = firmware[PAGE_SIZE * (main_prot.size_to_write - j) : PAGE_SIZE * (main_prot.size_to_write - j + 1)]
                for i in range(PAGE_SIZE):
                    temp_fw.insert(0, int(firmware[(main_prot.size_to_write - j) * PAGE_SIZE + PAGE_SIZE - i - 1]))
                temp_fw.append(0x45)
                crc = calc_crc(temp_fw)
                temp_fw.insert(0, crc)
                temp_fw.insert(0, 0)
                temp_fw.insert(0, 1)
                temp_fw.insert(0, 0x55)

                temp_fw.append(0x6e)
                temp_fw.append(0x64)

            if j == 2:
                print("Are you prepared??")
            temp_fw = parser.prepare_protocol_unit(temp_fw, 13, 0, 0)
            ser.write(temp_fw)
            print(temp_fw)
            print("\n")
            j -= 1
            temp_fw = []
            crc = 0
            protocol.can_we_continue = False
        else:
            root.update_idletasks()
            root.update()
            if ser.inWaiting():  # Rx buffer isn't empty
                mas.append(ser.read())  # Read 1 byte
            if mas != [] and ser.inWaiting() == 0:  # If pocket finish make an output
                write_to_editor("Received:\n")  # вставка в конец
                # print("New arrival!")
                for val in mas:
                    temp_rx.append(bytes_to_int(val))
                write_to_editor(mas)
                write_to_editor('\n')
                # print(mas)
                stringlist = converter.output_list_of_bytes_as_string(mas)
                # if stringlist == "\x24\x10\x02\x02\x00\x04\x00\x30":
                #     print(stringlist)
                # if mas[0] == b'\x24':
                #     print("Cmd received.")
                for val_int in temp_rx:
                    write_to_editor(str("%02X" % (val_int)))
                    # print("{%02X}"%(val_int))
                write_to_editor('\n')
                mas = []
                temp_rx = []
            status_po = parser.parse_cmd(stringlist, main_prot)
            if status_po != parser.Status.STATUS_OK and status_po != parser.Status.STATUS_NOT_ENOUGH_DATA:
                stringlist = ""


def bytes_to_int(bytes):
    result = 0
    for b in bytes:
        result = result * 256 + int(b)
    return result


def click_btn_send(event):
    i = 0
    cmd_to_send = entry_cmd.get()
    base16INTmas = []
    hex_value_mas = []
    while i < len(cmd_to_send) - 1:
        base16INTmas.insert(0, (int(cmd_to_send[len(cmd_to_send) - 2 - i]) << 4) + int(cmd_to_send[len(cmd_to_send) - i - 1], 16))
        i = i + 2
    if len(cmd_to_send) % 2 != 0:
        base16INTmas.insert(0, int(cmd_to_send[0]))
    for int_val in base16INTmas:
        hex_value_mas.append(hex(int_val))
    # print(base16INTmas)
    print(hex_value_mas)
    # base16INT = int(cmd_to_send, 16)
    # print(base16INT)
    # hex_value = hex(base16INT)
    ser.write(base16INTmas)


def calc_crc(data_mas):
    crc = 0
    for x in data_mas:
        crc = crc ^ x
    return crc


def calc_crc32(data_mas):
    temp_len = len(data_mas)
    temp_len32 = math.ceil(temp_len/4)
    temp_word = np.uint32(0x0)
    temp_crc = np.uint32(0x0)
    for i in range(temp_len32 - 1):
        temp_word = np.uint32(data_mas[4 * i]) + np.uint32(data_mas[4 * i + 1] << 8)\
                    + np.uint32(data_mas[4 * i + 2] << 16) + np.uint32(data_mas[4 * i + 3] << 24)
        temp_crc = temp_crc ^ temp_word
        temp_word = np.uint32(0x0)

    if temp_len - (round(temp_len / 4) * 4) is 0:
        temp_word = np.uint32(data_mas[4 * (temp_len32 - 1)]) + np.uint32(data_mas[4 * (temp_len32 - 1) + 1] << 8)\
                    + np.uint32(data_mas[4 * (temp_len32 - 1) + 2] << 16) + np.uint32(data_mas[4 * (temp_len32 - 1) + 3] << 24)
    else:
        for j in range(temp_len - (round(temp_len / 4) * 4)):
            temp_word = temp_word + np.uint32((datamas[(temp_len32 - 1) * 4 + j] << 8 * j))

    temp_crc = temp_crc ^ temp_word

    return temp_crc


root = Tk()
root.title("Lns User Interface")
# Main window size
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
w = 600
h = 450
x = (sw - w) / 2
y = (sh - h) / 2
root.geometry('%dx%d+%d+%d' % (w, h, x, y))
root.resizable(False, False)
# Frame
frame = ttk.Frame(root, borderwidth=1, relief=SOLID, padding=[8, 10])
# Objects
combo_ports = ttk.Combobox(frame, width=30)
# combo_ports.pack(anchor="nw")
combo_ports.grid(row=1, column=1, pady=15)
btn_scan = ttk.Button(frame, text="Rescan")
btn_scan.grid(row=1, column=2, padx=5)
#btn_scan.pack(anchor="n")
btn_scan.bind("<ButtonPress-1>", click_btn_scan)
btn_con = ttk.Button(frame, text="Connect")
btn_con.grid(row=1, column=3)
#btn_con.pack(anchor="n")
btn_con.bind("<ButtonPress-1>", click_btn_con)
entry_cmd = ttk.Entry(frame, text="test", width=33)
entry_cmd.grid(row=2, column=1, pady=15)
#entry_cmd.pack()
btn_send = ttk.Button(frame, text="Send")
btn_send.grid(row=2, column=2)
btn_send.bind("<ButtonPress-1>", click_btn_send)
btn_upd = ttk.Button(frame, text="Update Sw")
btn_upd.grid(row=2, column=3)
btn_upd.bind("<ButtonPress-1>", click_btn_upd)
editor = ScrolledText(frame, height=10, width=50, wrap="char")
editor.grid(row=3, column=1, columnspan=3)
frame.pack(anchor=NW, fill=X, padx=5, pady=5)
ser = serial.Serial()
mas = []
temp = []
stringlist = ""
status_po = parser.Status.STATUS_OK
main_prot = parser.Protocol()
# root.mainloop()
while 1:
    root.update_idletasks()
    root.update()

    if ser.is_open:

        if ser.inWaiting():                                              # Rx buffer isn't empty
            mas.append(ser.read())                                       # Read 1 byte
        if mas != [] and ser.inWaiting() == 0:                           # If pocket finish make an output
            write_to_editor("Received:\n")  # вставка в конец
            # print("New arrival!")
            for val in mas:
                temp.append(bytes_to_int(val))
            write_to_editor(mas)
            write_to_editor('\n')
            # print(mas)
            stringlist = converter.output_list_of_bytes_as_string(mas)
            # if stringlist == "\x24\x10\x02\x02\x00\x04\x00\x30":
            #     print(stringlist)
            # if mas[0] == b'\x24':
            #     print("Cmd received.")
            for val_int in temp:
                write_to_editor(str("%02X"%(val_int)))
                # print("{%02X}"%(val_int))
            write_to_editor('\n')
            mas = []
            temp = []
        status_po = parser.parse_cmd(stringlist, main_prot)
        if status_po != parser.Status.STATUS_OK and status_po != parser.Status.STATUS_NOT_ENOUGH_DATA:
            stringlist = ""

