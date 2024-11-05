import logging
import time
import math
from threading import Lock

class T5UIC1_LCD:
    """
    Class representing the control interface for a T5UIC14 LCD display.
    (https://www.dwin-global.com/uploads/T5L_TA-Instruction-Set-Development-Guide.pdf)
    """

    address = 0x2A
    RECEVIED_NO_DATA = 0x00
    RECEIVED_SHAKE_HAND_ACK = 0x01

    # Display resolution
    screen_width = 272
    screen_height = 480

    # Data frame structure
    data_frame_head = b"\xAA"
    data_frame_tail = [0xCC, 0x33, 0xC3, 0x3C]
    data_frame = []

    # 3-.0：The font size, 0x00-0x09, corresponds to the font size below:
    # 0x00=6*12   0x01=8*16   0x02=10*20  0x03=12*24  0x04=14*28
    # 0x05=16*32  0x06=20*40  0x07=24*48  0x08=28*56  0x09=32*64

    # no 8x8
    font6x12 = 0x00
    font8x16 = 0x01
    font10x20 = 0x02
    font12x24 = 0x03
    font14x28 = 0x04
    font16x32 = 0x05
    font20x40 = 0x06
    font24x48 = 0x07
    font28x56 = 0x08
    font32x64 = 0x09

    # Colors
    color_black = 0x0000
    color_white = 0xFFFF
    color_yellow = 0xFF0F
    color_bg_window = 0x31E8   # Popup background color
    color_bg_blue = 0x1125     # Dark blue background color
    color_bg_black = 0x0841    # Black background color
    color_bg_red = 0xF00F      # Red background color
    popup_text_color = 0xD6BA  # Popup font background color
    line_color = 0x3A6A        # Split line color
    rectangle_color = 0xEE2F   # Blue square cursor color
    percent_color = 0xFE29     # Percentage color
    barFill_color = 0x10E4     # Fill color of progress bar
    select_color = 0x33BB      # Selected color

    DWIN_FONT_MENU = font8x16
    DWIN_FONT_STAT = font10x20
    DWIN_FONT_HEAD = font10x20

    # Instructions
    cmd_handshake = 0x00
    cmd_clear = 0x01
    cmd_draw_point = 0x02
    cmd_draw_line = 0x03
    cmd_draw_rect = 0x05
    cmd_draw_value = 0x14
    cmd_frame_setdir = 0x34
    cmd_update_lcd = 0x3d
    cmd_set_palette = 0x40
    cmd_draw_line = 0x51
    cmd_clear_screen = 0x52
    cmd_draw_rectangle = 0x59
    cmd_fill_rectangle = 0x5B
    cmd_reverse_color_area = 0x5C
    # cmd_backlight_brightness = 0x5F
    cmd_backlight_brightness = 0x30
    cmd_move_screen_area = 0x09
    #cmd_draw_icon = 0x97
    cmd_draw_icon = 0x23
    #cmd_draw_text = 0x98
    cmd_draw_text = 0x11
    cmd_draw_int = 0x14
    # cmd_show_image = 0x70
    cmd_show_image = 0x2200
    cmd_jpeg_showandcache = 0x2200

    # Alias for extra commands
    direction_up = 0x02
    direction_down = 0x03


    def __init__(self, serial):
        """
        Initializes the LCD object.

        Args:
            serial : Serial object to send messages.
        """
        self.serial_data = bytearray()
        self.lock = Lock()
        self.serial = serial
        self.logging = True
        logging.info("init T5UIC1_LCD")
        self.serial.register_callback(
            self._handle_serial_read)
    
    def init_display(self):
        self.log("entering init_display")
        self.log("Sending handshake... ")
        while not self.handshake():
            pass
        self.log("Handshake response: OK.")
        self.jpg_showandcache(0)
        self.frame_setdir(1)
        self.update_lcd();

    def byte(self, bool_val):
        """
        Appends a single-byte value to the data frame.

        :param bval: The byte value to be appended.
        :type bval: int
        """
        self.data_frame += int(bool_val).to_bytes(1, byteorder="big")

    def word(self, word_val):
        """
        Appends a two-byte value to the data frame.

        :param wval: The two-byte value to be appended.
        :type wval: int
        """
        self.data_frame += int(word_val).to_bytes(2, byteorder="big")

    def long(self, long_val):
        """
        Appends a four-byte value to the data frame.

        :param lval: The four-byte value to be appended.
        :type lval: int
        """
        self.data_frame += int(long_val).to_bytes(4, byteorder="big")

    def double_64(self, double_val):
        """
        Appends an eight-byte value to the data frame.

        :param dval: The eight-byte value to be appended.
        :type value: int
        """
        self.data_frame += int(double_val).to_bytes(8, byteorder="big")

    def string(self, string):
        """
        Appends a UTF-8 encoded string to the data frame.

        :param string: The string to be appended.
        :type string: str
        """
        self.data_frame += string.encode("utf-8")

    def send(self):
        """
        Sends the prepared data frame to the display according to the T5L_TA serial protocol.

        Sends the current contents of the data frame, followed by a predefined
        tail sequence. After sending, the data frame is reset to the head sequence.
        """
        # Write the current data frame and tail sequence to the serial connection
        self.serial.write(self.data_frame)
        self.serial.write(self.data_frame_tail)

        # Reset the data frame to the head sequence for the next transmission
        self.data_frame = self.data_frame_head

        # Delay to allow for proper transmission
        time.sleep(0.001)

    def handshake(self):
        """
        Perform a handshake with the display.

        :return: True if handshake is successful, otherwise False.
        :rtype: bool
        """
        # Send the initiation byte (0x00)
        self.log("handshake")
        self.byte(self.cmd_handshake)
        self.send()
        time.sleep(0.1)

        max_retry = 26
        req = 0
        databuf = [None] * max_retry
        while (req<max_retry):
                data_read = self._serial_read() 
                if len(data_read) > 0:
                        databuf[req] = struct.unpack('B', data_read)[0] 
                        if databuf[0] != 0xAA:
                                if (recnum>0):
                                        req=0
                                        databuf = [None] * max_retry
                                continue
                time.sleep(.020)
                req += 1
        retval = (req>=3 and databuf[0] == 0xAA and databuf[1] == 0 and chr(databuf[2]) == 'O' and chr(databuf[3]) == 'K')
        self.log("handshake " + str(retval))
        return retval

        # return True

    # Set screen display direction
    #  dir: 0=0°, 1=90°, 2=180°, 3=270°
    def frame_setdir(self, dir):
        self.log("frame_setdir")
        self.byte(self.cmd_frame_setdir)
        self.byte(0x5A)
        self.byte(0xA5)
        self.byte(dir)
        self.send()

    def update_lcd(self):
        self.log("update_lcd")
        self.byte(self.cmd_update_lcd)
        self.send()

    def set_backlight_brightness(self, brightness):
        """
        Set the backlight luminance.

        :param luminance: Luminance level (0x00-0xff).
        :type luminance: int
        """
        self.log("backlight_brightness")
        self.byte(self.cmd_backlight_brightness)
        self.byte(max(brightness, 0x1f))
        self.send()

    def jpg_showandcache(self, id):
        self.log("jpg_showandcache")
        self.word(self.cmd_jpeg_showandcache)
        self.byte(id)
        self.send()

    def set_palette(self, background_color=color_black, foreground_color=color_white):
        """
        Set the palette colors for drawing functions.

        :param bg_color: Background color.
        :type bg_color: int
        :param front_color: Foreground (text) color.
        :type front_color: int
        """
        self.log("set_platette")
        self.byte(self.cmd_set_palette)
        self.word(foreground_color)
        self.word(background_color)
        self.send()

    def clear_screen(self, color=color_black):
        """
        Clear the screen with a specified color.

        :param color: Background color.
        :type color: int
        """
        self.log("clear screen")
        self.byte(self.cmd_clear_screen)
        self.word(color)
        self.send()

    def draw_point(self, color, w_x, w_y, p_x, p_y):
        """
        Draw a point on the screen.

        :param Color: Color of the point.
        :type Color: int
        :param x: X-coordinate of the point.
        :type x: int
        :param y: Y-coordinate of the point.
        :type y: int
        """
        self.log("draw point")
        self.byte(self.cmd_draw_line)
        self.word(color)
        self.byte(w_x) # x width
        self.byte(w_y) # y width
        self.word(int(p_x))
        self.word(int(p_y))
        self.send()

    def draw_line(self, color, x_start, y_start, x_end, y_end):
        """
        Draw a line segment on the screen.

        :param color: Line segment color.
        :type color: int
        :param x_start: X-coordinate of the starting point.
        :type x_start: int
        :param y_start: Y-coordinate of the starting point.
        :type y_start: int
        :param x_end: X-coordinate of the ending point.
        :type x_end: int
        :param y_end: Y-coordinate of the ending point.
        :type y_end: int
        """
        self.log("draw line")
        self.byte(self.cmd_draw_line)
        self.word(color)
        self.word(x_start)
        self.word(y_start)
        self.word(x_end)
        self.word(y_end)
        self.send()

    def draw_rectangle(self, mode, color, x_start, y_start, x_end, y_end):
        """
        Draw a rectangle on the screen.

        :param mode: 0=frame, 1=fill, 2=XOR fill.
        :type mode: int
        :param color: Rectangle color.
        :type color: int
        :param x_start: X-coordinate of the upper-left point.
        :type x_start: int
        :param y_start: Y-coordinate of the upper-left point.
        :type y_start: int
        :param x_end: X-coordinate of the lower-right point.
        :type x_end: int
        :param y_end: Y-coordinate of the lower-right point.
        :type y_end: int
        """
        self.log("draw rect")
        self.set_palette(self.color_white, color)
        mode_to_command = {
            0: self.cmd_draw_rectangle,
            1: self.cmd_fill_rectangle,
            2: self.cmd_reverse_color_area,
        }
        command = mode_to_command.get(mode, 0)
        self.byte(self.cmd_draw_rect)
        self.byte(mode)
        self.word(x_start)
        self.word(y_start)
        self.word(x_end)
        self.word(y_end)
        self.send()

    def draw_circle(self, color, x_center, y_center, r):
        """
        Draw a circle on the screen using the draw points method.

        :param Color: Circle color.
        :type Color: int
        :param x_center: X-coordinate of the center of the circle.
        :type x_center: int
        :param y_center: Y-coordinate of the center of the circle.
        :type y_center: int
        :param r: Circle radius.
        :type r: int
        """
        b = 0
        a = 0
        while a <= b:
            b = math.sqrt(r * r - a * a)
            while a == 0:
                b = b - 1
                break
            self.draw_point(
                color, 1, 1, x_center + a, y_center + b
            )  # Draw some sector 1
            self.draw_point(
                color, 1, 1, x_center + b, y_center + a
            )  # Draw some sector 2
            self.draw_point(
                color, 1, 1, x_center + b, y_center - a
            )  # Draw some sector 3
            self.draw_point(
                color, 1, 1, x_center + a, y_center - b
            )  # Draw some sector 4

            self.draw_point(
                color, 1, 1, x_center - a, y_center - b
            )  # Draw some sector 5
            self.draw_point(
                color, 1, 1, x_center - b, y_center - a
            )  # Draw some sector 6
            self.draw_point(
                color, 1, 1, x_center - b, y_center + a
            )  # Draw some sector 7
            self.draw_point(
                color, 1, 1, x_center - a, y_center + b
            )  # Draw some sector 8
            a += 1

    def fill_circle(self, font_color, x_center, y_center, r):
        """
        Fill a circle with a color.

        :param font_color: Fill color.
        :type font_color: int
        :param x_center: X-coordinate of the center of the circle.
        :type x_center: int
        :param y_center: Y-coordinate of the center of the circle.
        :type y_center: int
        :param r: Circle radius.
        :type r: int
        """
        b = 0
        for i in range(r, 0, -1):
            a = 0
            while a <= b:
                b = math.sqrt(i * i - a * a)
                while a == 0:
                    b = b - 1
                    break
                self.draw_point(
                    font_color, 2, 2, x_center + a, y_center + b
                )  # Draw some sector 1
                self.draw_point(
                    font_color, 2, 2, x_center + b, y_center + a
                )  # raw some sector 2
                self.draw_point(
                    font_color, 2, 2, x_center + b, y_center - a
                )  # Draw some sector 3
                self.draw_point(
                    font_color, 2, 2, x_center + a, y_center - b
                )  # Draw some sector 4

                self.draw_point(
                    font_color, 2, 2, x_center - a, y_center - b
                )  # Draw some sector 5
                self.draw_point(
                    font_color, 2, 2, x_center - b, y_center - a
                )  # Draw some sector 6
                self.draw_point(
                    font_color, 2, 2, x_center - b, y_center + a
                )  # Draw some sector 7
                self.draw_point(
                    font_color, 2, 2, x_center - a, y_center + b
                )  # Draw some sector 8
                a = a + 2

    def draw_string(
        self, show_background, size, font_color, background_color, x, y, string
    ):
        """
        Draw a string on the screen.

        :param show_background: True to display the background color, False to not display the background color.
        :type show_background: bool
        :param size: Font size.
        :type size: int
        :param font_color: Character color.
        :type font_color: int
        :param background_color: Background color.
        :type background_color: int
        :param x: X-coordinate of the upper-left point.
        :type x: int
        :param y: Y-coordinate of the upper-left point.
        :type y: int
        :param string: The string to be drawn.
        :type string: str
        """

        width_adjust=1
        self.log("draw text")
        self.byte(self.cmd_draw_text)
        # bit 7 : width_adjust
        # bit 6 : show
        # bit 4-5: unused 0
        # bit 0-3: size 
        self.byte(size | (show_background * 0x40) | (width_adjust * 0x80))  # mode (bshow)
        self.word(font_color)
        self.word(background_color)
        self.word(x)
        self.word(y)
        self.string(string[:40])
        self.send()

    def draw_int_value(
        self,
        show_background,
        zeroFill,
        zeroMode,
        font_size,
        color,
        background_color,
        iNum,
        x,
        y,
        value,
    ):
        """
        Draw a positive integer value on the screen.

        :param show_background: True to display the background color, False to not display the background color.
        :type show_background: bool
        :param zeroFill: True to zero fill, False for no zero fill.
        :type zeroFill: bool
        :param zeroMode: 1 for leading 0 displayed as 0, 0 for leading 0 displayed as a space.
        :type zeroMode: int
        :param font_size: Font size.
        :type font_size: int
        :param color: Character color.
        :type color: int
        :param background_color: Background color.
        :type background_color: int
        :param iNum: Number of digits.
        :type iNum: int
        :param x: X-coordinate of the upper-left point.
        :type x: int
        :param y: Y-coordinate of the upper-left point.
        :type y: int
        :param value: Integer value.
        :type value: int
        """
        self.log("draw int")
        self.byte(self.cmd_draw_int)
        # Bit 7: bshow
        # Bit 6: 1 = signed; 0 = unsigned number;
        # Bit 5: zeroFill
        # Bit 4: zeroMode
        # Bit 3-0: size
        self.byte(
            (show_background * 0x80)
            | (0 * 0x40)
            | (zeroFill * 0x20)
            | (zeroMode * 0x10)
            | font_size
        )
        self.word(color)
        self.word(background_color)
        self.byte(iNum)
        self.byte(0)  # fNum
        self.word(x)
        self.word(y)
        self.double_64(value)
        self.send()

    def draw_float_value(
        self,
        show_background,
        zeroFill,
        zeroMode,
        size,
        color,
        background_color,
        iNum,
        fNum,
        x,
        y,
        value,
    ):
        """
        Draw a floating point number on the screen.

        :param show_background: True to display the background color, False to not display the background color.
        :type show_background: bool
        :param zeroFill: True to zero fill, False for no zero fill.
        :type zeroFill: bool
        :param zeroMode: 1 for leading 0 displayed as 0, 0 for leading 0 displayed as a space.
        :type zeroMode: int
        :param size: Font size.
        :type size: int
        :param color: Character color.
        :type color: int
        :param background_color: Background color.
        :type background_color: int
        :param iNum: Number of whole digits.
        :type iNum: int
        :param fNum: Number of decimal digits.
        :type fNum: int
        :param x: X-coordinate of the upper-left point.
        :type x: int
        :param y: Y-coordinate of the upper-left point.
        :type y: int
        :param value: Float value.
        :type value: float
        """
        self.log("draw float")
        self.byte(self.cmd_draw_value)
        # Bit 7: bshow
        # Bit 6: 1 = signed; 0 = unsigned number;
        # Bit 5: zeroFill
        # Bit 4: zeroMode
        # Bit 3-0: size
        self.byte(
            (show_background * 0x80)
            | (0 * 0x40)
            | (zeroFill * 0x20)
            | (zeroMode * 0x10)
            | size
        )
        self.word(color)
        self.word(background_color)
        self.byte(iNum)
        self.byte(fNum)
        self.word(x)
        self.word(y)
        self.long(value)
        self.send()

    def draw_signed_float(
        self, show_background, size, color, background_color, iNum, fNum, x, y, value
    ):
        """
        Draw a signed floating-point number on the screen.

        :param size: Font size.
        :type size: int
        :param background_color: Background color.
        :type background_color: int
        :param iNum: Number of whole digits.
        :type iNum: int
        :param fNum: Number of decimal digits.
        :type fNum: int
        :param x: X-coordinate of the upper-left corner.
        :type x: int
        :param y: Y-coordinate of the upper-left corner.
        :type y: int
        :param value: Floating-point value to be displayed.
        :type value: float
        """
        if value < 0:
            self.draw_string(
                show_background, size, color, background_color, x - 6, y - 3, "-"
            )
            self.draw_float_value(
                show_background,
                False,
                0,
                size,
                color,
                background_color,
                iNum,
                fNum,
                x,
                y,
                -value,
            )
        else:
            self.draw_string(
                show_background, size, color, background_color, x - 6, y - 3, " "
            )
            self.draw_float_value(
                show_background,
                False,
                0,
                size,
                color,
                background_color,
                iNum,
                fNum,
                x,
                y,
                value,
            )

    def draw_icon(self, show_background, libID, picID, x, y):
        """
        Draw an icon on the screen.

        :param show_background: True to display the background color, False to not display the background color.
        :type show_background: bool
        :param libID: Icon library ID.
        :type libID: int
        :param picID: Icon ID.
        :type picID: int
        :param x: X-coordinate of the upper-left corner.
        :type x: int
        :param y: Y-coordinate of the upper-left corner.
        :type y: int
        """
        self.log("draw icon")
        if x > self.screen_width - 1:
            x = self.screen_width - 1
        if y > self.screen_height - 1:
            y = self.screen_height - 1
        self.byte(self.cmd_draw_icon)
        self.word(x)
        self.word(y)
        self.byte(libID)
        # self.byte(show_background * 0x01)
        self.word(picID)
        self.send()

    def draw_image(self, id=1):
        """
        Draw a JPG image on the screen and cache it in the virtual display area.

        :param id: Picture ID.
        :type id: int
        """
        self.log("show image")
        self.byte(self.cmd_show_image)
        self.byte(id)
        self.send()

    def move_screen_area(
        self, direction, offset, background_color, x_start, y_start, x_end, y_end
    ):
        """
        Copy an area from the virtual display area to the current screen.

        :param direction: Direction ( 0 = ,1 =, 0x02= top, 0x03 = down)
        :type direction: int
        :param offset: How many pixels the copied area is going to be moved.
        :type offset: int
        :param offset: Color of background (to fill the previously moved area?).
        :type offset: int
        :param x_start: X-coordinate of the upper-left corner of the virtual area.
        :type x_start: int
        :param y_start: Y-coordinate of the upper-left corner of the virtual area.
        :type y_start: int
        :param x_end: X-coordinate of the lower-right corner of the virtual area.
        :type x_end: int
        :param y_end: Y-coordinate of the lower-right corner of the virtual area.
        :type y_end: int
        """
        self.log("move screen area")
        self.byte(self.cmd_move_screen_area)
        # mode 0: circle shift, 1: translation, mode << 7
        self.byte(0x80 | direction)
        self.word(offset)
        self.word(background_color)
        self.word(x_start)
        self.word(y_start)
        self.word(x_end)
        self.word(y_end)
        self.send()

    def log(self, msg, *args, **kwargs):
        if self.logging:
            logging.info("T5UIC1 LCD: " + str(msg))
    
    def error(self, msg, *args, **kwargs):
        logging.error("T5UIC1 LCD: " + str(msg))

    def _handle_serial_read(self, data):
        self.lock.acquire()
        for byte in data:
            self.serial_data.append(byte)
        self.lock.release()
        byte_debug = ' '.join(['0x{:02x}'.format(byte) for byte in data])
        log("Received message: " + byte_debug)

    def _serial_read(self):
        self.lock.acquire()
        data = self.serial_data
        self.serial_data = bytearray()
        self.lock.release()
        return data
