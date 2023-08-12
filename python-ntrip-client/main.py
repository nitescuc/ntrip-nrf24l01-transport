import os
import sys
import traceback
import time
import pigpio
from nrf24 import *
from ntrip_client import NTRIPClient

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

PIO_HOSTNAME = os.getenv('PIO_HOSTNAME', 'localhost')
PIO_PORT = int(os.getenv('PIO_PORT', '8888'))
ADDRESS = os.getenv('RF_ADDRESS', 'NTRIP')
NTRIP_HOST = os.getenv('NTRIP_HOST')
NTRIP_PORT = int(os.getenv('NTRIP_PORT', '2101'))
NTRIP_MOUNTPOINT = os.getenv('NTRIP_MOUNTPOINT')
NTRIP_USERNAME = os.getenv('NTRIP_USERNAME')
NTRIP_PASSWORD = os.getenv('NTRIP_PASSWORD')

if __name__ == "__main__":
    hostname = PIO_HOSTNAME
    port = PIO_PORT
    address = ADDRESS

    if not (2 < len(address) < 6):
        print(f'Invalid address {address}. Addresses must be 3 to 5 ASCII characters.')
        sys.exit(1)

    # Connect to pigpiod
    print(f'Connecting to GPIO daemon on {hostname}:{port} ...')
    pi = pigpio.pi(hostname, port)
    if not pi.connected:
        print("Not connected to Raspberry Pi ... goodbye.")
        sys.exit()

    ntrip_client = NTRIPClient(NTRIP_HOST, NTRIP_PORT, NTRIP_MOUNTPOINT, None, NTRIP_USERNAME, NTRIP_PASSWORD)
    if not ntrip_client.connect():
        print("Not connected to NTRIP server ... goodbye.")
        sys.exit()

    # Create NRF24 object.
    # PLEASE NOTE: PA level is set to MIN, because test sender/receivers are often close to each other, and then MIN works better.
    nrf = NRF24(pi, ce=25, payload_size=RF24_PAYLOAD.DYNAMIC, channel=100, data_rate=RF24_DATA_RATE.RATE_250KBPS, pa_level=RF24_PA.HIGH)
    nrf.set_address_bytes(len(address))
    nrf.open_writing_pipe(address)
    
    # Display the content of NRF24L01 device registers.
    nrf.show_registers()

    try:
        print(f'Send to NRF24 {address}')
        count = 0
        while True:
            for raw_rtcm in ntrip_client.recv_rtcm():
                # each raw_rtcm is a bytes object containing a single RTCM message
                # print(f'Got RTCM message {raw_rtcm}')
                for i in range(0, len(raw_rtcm), 32):
                    # print(f'Sending {raw_rtcm[i:i+32]}')
                    nrf.reset_packages_lost()
                    nrf.send(raw_rtcm[i:i+32])
                    try:
                        nrf.wait_until_sent()
                    except TimeoutError:
                        print('Timeout waiting for transmission to complete.')
                        # Wait 10 seconds before sending the next reading.
                        time.sleep(10)
                        continue
    except:
        traceback.print_exc()
        nrf.power_down()
        pi.stop()
        ntrip_client.shutdown()
