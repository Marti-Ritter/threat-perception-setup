import serial
import struct

ser = serial.Serial(
    port='COM6',
)
#      case 'O': // USB initiated new connection; reset all state variables
#      case 'S': // Start/Stop data streaming
#      case 'E': // Start/Stop threshold event detection + transmission
#      case 'L': // Start/Stop logging data from active channels to microSD card
#      case 'C': // Set subset of channels to stream raw data (USB and module)
#      case 'R': // Select ADC Voltage range for each channel
#      case 'A': // Set max number of actively sampled channels
#      case 'D': // Read SD card and send data to USB
#      case 'F': // Change sampling frequency

print(ser.isOpen())
thestring = "O"
ser.write(thestring.encode())
s = ser.read()
print(s)
ser.close()

