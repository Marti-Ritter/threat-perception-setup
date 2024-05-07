import multiprocessing
import pygame
from threading import Timer
from pandas import DataFrame
import TPM_Utility
import time
import random as rdm
import csv


# accurate up until 200sps, maximum 400sps
def analog_recorder_func(instructions, go_event, current_line, instruction_pipe, lick_inputs, target_sps=200):
    # Initialization
    start_time = time.perf_counter()
    output_file = None
    writer = None
    paused = True
    counter = 0

    mouse_lick_in = lick_inputs[0]
    rat_lick_in = lick_inputs[1]

    # Prepare the i2c communication
    import board
    import busio
    i2c = busio.I2C(board.SCL, board.SDA)
    print("I2C initialized.")

    # Prepare the ADC-object
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    ads = ADS.ADS1115(i2c)
    ads.gain = 2 / 3
    print("ADC initialized.")

    # Prepare position channel to be read
    position_channel = AnalogIn(ads, ADS.P0)
    velocity_channel = AnalogIn(ads, ADS.P1)
    print("Channels initialized.")

    # Prepare to read the lick-inputs
    import pigpio
    pi = pigpio.pi()
    pi.set_mode(mouse_lick_in, pigpio.INPUT)
    pi.set_pull_up_down(mouse_lick_in, pigpio.PUD_DOWN)
    pi.set_mode(rat_lick_in, pigpio.INPUT)
    pi.set_pull_up_down(rat_lick_in, pigpio.PUD_DOWN)
    print("PiGPIO input initialized.")

    target = 1. / target_sps
    end = time.perf_counter() + target

    while True:
        # Check for new instructions
        if instruction_pipe.poll():
            command = instruction_pipe.recv()
            if command is instructions.Pause:
                paused = True
            elif command is instructions.Ready:
                paused = False
                go_event.wait()
                start_time = time.perf_counter()
            elif command is instructions.Reset:
                if output_file:
                    output_file.close()
                print('DROPPED ' + str(counter) + ' LINES.')
                file_location = instruction_pipe.recv()
                output_file = open(file_location, 'w')
                writer = csv.DictWriter(output_file,
                                        fieldnames=['Timestamp', 'Position', 'Speed', 'Mouse Lick', 'Rat Lick'],
                                        lineterminator='\n')
                writer.writeheader()
                counter = 0
                paused = True
            elif command is instructions.SamplingRate:
                target_sps = instruction_pipe.recv()
                target = 1. / target_sps
            elif command is instructions.Stop:
                break
            else:
                raise ValueError(f'Unknown command received: {command}')

        if paused:
            time.sleep(0.05)
            continue

        if time.perf_counter() > end:
            timestamp = time.perf_counter() - start_time
            new_position = position_channel.voltage
            new_speed = velocity_channel.voltage
            mouse_lick = pi.read(mouse_lick_in)
            rat_lick = pi.read(rat_lick_in)

            current_line[0:3] = [timestamp, new_position, mouse_lick]

            row_dict = {
                'Timestamp': timestamp,
                'Position': new_position,
                'Speed': new_speed,
                'Mouse Lick': mouse_lick,
                'Rat Lick': rat_lick
            }
            writer.writerow(row_dict)
            counter += 1

            end = time.perf_counter() + target
            time.sleep(target * 0.8)

    print(counter)
    print('RECORDER STOPPED.')


# records as fast as possible, between 20-30ksps
def unlimited_recorder_func(instructions, go_event, current_line, instruction_pipe):
    # Initialization
    start_time = time.perf_counter()
    output_file = None
    writer = None
    paused = True
    counter = 0

    while True:
        # Check for new instructions
        if instruction_pipe.poll():
            command = instruction_pipe.recv()
            if command is instructions.Pause:
                paused = True
            elif command is instructions.Ready:
                paused = False
                go_event.wait()
                start_time = time.perf_counter()
            elif command is instructions.Reset:
                if output_file:
                    output_file.close()
                print('DROPPED ' + str(counter) + ' LINES.')
                file_location = instruction_pipe.recv()
                output_file = open(file_location, 'w')
                writer = csv.DictWriter(output_file, fieldnames=['Timestamp', 'Position', 'Speed', 'whatever'],
                                        lineterminator='\n')
                writer.writeheader()
                counter = 0
                paused = True
            elif command is instructions.Stop:
                break
            else:
                raise ValueError(f'Unknown command received: {command}')

        if paused:
            continue

        timestamp = time.perf_counter() - start_time
        new_position = rdm.random()
        new_speed = rdm.random()

        current_line[0:3] = [timestamp, new_position, new_speed]

        row_dict = {
            'Timestamp': timestamp,
            'Position': new_position,
            'Speed': new_speed,
            'whatever': counter
        }
        writer.writerow(row_dict)
        counter += 1

    print(counter)
    print('RECORDER STOPPED.')


# virtual recorder, reads from pygame inputs
def virtual_recorder_func(instructions, go_event, current_line, instruction_pipe, mouse_input_queue, target_sps=200):
    # Initialization
    start_time = time.perf_counter()
    output_file = None
    writer = None
    paused = True
    counter = 0

    target = 1. / target_sps
    end = time.perf_counter() + target

    virtual_position = 0  # in cm
    virtual_speed = 0  # in cm/s

    while True:
        # Check for new instructions
        if instruction_pipe.poll():
            command = instruction_pipe.recv()
            if command is instructions.Pause:
                paused = True
            elif command is instructions.Ready:
                paused = False
                go_event.wait()
                start_time = time.perf_counter()
            elif command is instructions.Reset:
                if output_file:
                    output_file.close()
                print('DROPPED ' + str(counter) + ' LINES.')
                output_file = open('virtual_records.csv', 'w')
                writer = csv.DictWriter(output_file, fieldnames=['Timestamp', 'Position', 'Speed', 'whatever'],
                                        lineterminator='\n')
                writer.writeheader()
                counter = 0
                paused = True
            elif command is instructions.SamplingRate:
                target_sps = instruction_pipe.recv()
                target = 1. / target_sps
            elif command is instructions.Stop:
                break
            else:
                raise ValueError(f'Unknown command received: {command}')

        # Skip the rest of the process if paused
        if paused:
            continue

        if time.perf_counter() > end:

            while not mouse_input_queue.empty():
                # virtual input
                event_button = mouse_input_queue.get()
                if event_button == 4:
                    virtual_speed += 0.1
                elif event_button == 5:
                    virtual_speed -= 0.1

            timestamp = time.perf_counter() - start_time

            if virtual_speed < -2.5:
                virtual_speed = -2.5
            elif virtual_speed > 2.5:
                virtual_speed = 2.5

            virtual_position += virtual_speed * target

            if virtual_position < 0:
                virtual_position = 5
            if virtual_position > 5:
                virtual_position = 0

            current_line[0:3] = [timestamp, virtual_position, virtual_speed + 2.5]

            row_dict = {
                'Timestamp': timestamp,
                'Position': virtual_position,
                'Speed': virtual_speed,
                'whatever': counter
            }
            writer.writerow(row_dict)
            counter += 1

            end = time.perf_counter() + target
            time.sleep(target * 0.8)

    print(counter)
    print('RECORDER STOPPED.')


def trace_data(instructions, event_flags, from_recorder, instruction_pipe):
    # Initialization
    proto_records = []
    paused = False
    input_file = None
    FPS = 1
    skip = True
    event_flags.statistics_refresh_finished.set()

    def follow(file):
        file.seek(0, 0)  # Go to the start of the file
        while True:
            line = file.readline()
            if not line:
                yield None
                time.sleep(0.1)  # wait a moment
                continue
            yield line

    def refresh_screen():
        event_flags.statistics_refresh_finished.clear()
        t = Timer(1 / FPS, refresh_screen)
        t.daemon = True
        t.start()
        event_flags.statistics_refresh_finished.set()

    refresh_screen()

    while True:
        # Check for new instructions
        if instruction_pipe.poll():
            command = instruction_pipe.recv()
            if command is instructions.Pause:
                paused = True
            elif command is instructions.Go:
                paused = False
            elif command is instructions.Reset:
                proto_records = []
            elif command is instructions.Dump:
                df = DataFrame(proto_records)
                df.to_csv('TRACER.csv')
            elif command is instructions.Stop:
                break
            else:
                raise ValueError(f'Unknown command received: {command}')

        if paused:
            time.sleep(1 / 200)
            continue

        if from_recorder.poll():
            info = from_recorder.recv()
            if input_file:
                input_file.close()
            input_file = open(info[0], 'r')
            file_iterator = follow(input_file)
            columns = info[1]
            skip = True

        if input_file:
            event_flags.statistics_refresh_finished.wait()
            for i in file_iterator:
                if not i:
                    break
                if skip:
                    skip = False
                    continue
                linesplit = i.split(',')
                proto_records.append({
                    columns[0]: linesplit[0],
                    columns[1]: linesplit[1],
                    columns[2]: linesplit[2],
                    columns[3]: linesplit[3]
                })
        #print(f'read: {len(proto_records)} lines')
        #time.sleep(1 / 5)

    print(len(proto_records))
    print('TRACER STOPPED.')


def main():
    latest_line = multiprocessing.Array('f', 3)
    to_recorder, recorder_instructions = multiprocessing.Pipe()
    to_tracer, tracer_instructions = multiprocessing.Pipe()
    record_in, record_out = multiprocessing.Pipe()

    instructions = TPM_Utility.Instructions
    event_flags = TPM_Utility.EventFlags

    record_process = multiprocessing.Process(target=recorder_func, args=(instructions, record_in, latest_line,
                                                                         recorder_instructions,))
    trace_process = multiprocessing.Process(target=trace_data, args=(instructions, event_flags, record_out,
                                                                     tracer_instructions,))
    record_process.start()
    trace_process.start()

    for trial in range(1, 3):
        start_time = time.time()
        end_time = start_time + 3

        to_recorder.send(instructions.Reset)
        to_recorder.send((trial, 'bla'))
        to_tracer.send(instructions.Reset)

        while time.time() < end_time:
            pass

        to_recorder.send(instructions.Pause)
        time.sleep(2)
        to_tracer.send(instructions.Pause)
        time.sleep(2)
        to_recorder.send(instructions.Go)
        to_tracer.send(instructions.Go)

    to_tracer.send(instructions.Dump)
    print('tracer told to stop')
    to_tracer.send(instructions.Stop)
    print('recorder told to stop')
    to_recorder.send(instructions.Stop)
    trace_process.join()
    record_process.join()

    time.sleep(0.5)
    print('finished')


if __name__ == '__main__':
    main()