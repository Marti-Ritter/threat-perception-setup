import numpy as np
import time

from pypylon import pylon
from multiprocessing import Process, Array, Event, Pipe
from imageio import get_writer


class VideoSaveProcess(Process):
    """
    A small process that takes care of saving a video, so that the other processes can keep running.

    args:
    saving_location: A string describing the path to the saving location
    fps: FPS of the video to save
    record: an iterable containing a series of images (as array) that make up the video
    """

    def __init__(self, saving_location, fps, record):
        # set up all the relevant variables
        super(VideoSaveProcess, self).__init__()
        self.saving_location = saving_location
        self.fps = fps
        self.record = record

    def run(self):
        # when the process starts the file is saved with the previously defined variables
        with get_writer(self.saving_location, fps=self.fps) as writer:
            for image in self.record:
                writer.append_data(image)


class BaslerImageHandler(pylon.ImageEventHandler):
    """
    Subclass of pylon.ImageEventHandler which is used to process the grabbed frames from the camera assigned to its
    parent and store them optionally in a buffer if the recording bool was set.
    During recording it can also write to a meta-dictionary that includes information to this recording.
    Regardless of whether it is recording or not, it will write to the shared_array of the parent via an output_port.

    args:
    parent: The instance of BaslerCameraProcess that this object is assigned to.
    """

    def __init__(self, parent):
        super(BaslerImageHandler, self).__init__()

        # assign the parent's name and get an image port from the parent.
        self.name = getattr(parent, 'name')
        self.image_port = parent.get_image_port()

        # create the iamge-buffer and meta-dict
        self.buffer = []
        self.meta = {}

        # start with recording off
        self.recording = False

    def OnImagesSkipped(self, camera, countOfSkippedImages):
        # Print a message if an image was skipped. TODO: transfer to the meta_dict
        print(f'Camera {self.name} has skipped {countOfSkippedImages} images!\n')

    def OnImageGrabbed(self, camera, grabResult):
        # check if the grab of this frame succeeded
        if grabResult.GrabSucceeded():
            grabArray = grabResult.GetArray()
            # write the grabbed frame to the image_port. This is the only time a process writes to it.
            # Every other process should treat this as read-only!
            np.copyto(self.image_port, grabArray)

            # check if the recording bool was set
            if self.recording:
                # write to buffer and meta
                self.buffer.append(grabArray)
                self.meta[len(self.buffer)] = {
                    'NumberOfSkippedImages': grabResult.NumberOfSkippedImages,
                    'TimeStamp': grabResult.TimeStamp,
                }
        else:
            # Print a message if a grab failed. TODO: transfer to the meta_dict
            print("Error: ", grabResult.GetErrorCode(), grabResult.GetErrorDescription())

    def return_buffer(self):
        # used for handing the buffer over to the saving process above. This returns the buffer and resets it to empty.
        buffer = self.buffer
        self.buffer = []
        return buffer

    def set_recording(self, value):
        # used for setting the recording flag through the parent. Only boolean values are allowed.
        self.recording = value


class BaslerCameraProcess(Process):
    """
    Main multithreading.Process subclass which controls a camera which is assigned via the information given to it in a
    dict. Communication with this process happens via a pipe.
    """

    def __init__(self, initial_dict,  communication_pipe):
        super(BaslerCameraProcess, self).__init__()

        # extend the given dict with the shared array used to access this cameras live-feed and the info on how to build
        # an image_port from that.
        self.camera_dict = self.build_shared_array(initial_dict)
        self.pipe = communication_pipe

        # cannot be initiated during init, must be created after process starts
        self.camera = None
        self.image_event_handler = None

        # handle of the process used to save the recorded images.
        self.saving_process = None

        # boolean to handle process shutdown and a shared Event which is used to signal the readiness of the process
        # after incoming commands and after the inital setup.
        self.alive = True
        self.ready = Event()

    def build_shared_array(self, initial_dict):
        # to build the shared_array we need to know the size of the sensor. Since this property is not accessible while
        # the camera is inactive, we need to activate it for a moment and check the size, then deactivate it.
        camera = self.get_camera_by_index(initial_dict['assigned_camera_index'])
        # activate the camera.
        camera.Open()
        # load the settings in case there are Offsets or similarly relevant values changed.
        pylon.FeaturePersistence.Load("../Camera_Settings.pfs", camera.GetNodeMap())
        # get the shape of the sensor.
        shape = (self.get_camera_height(camera), self.get_camera_width(camera))
        # deactivate the camera.
        camera.Close()

        # set an array_type. This is only its own variable for easy modifications. In general this should be good enough
        # for storing image data.
        array_type = 'i'

        # arrays can't be 2-dimensional without creating multiple (think list of lists). To allow easy working with the
        # live-feed, this is created here as a 1D-array of the same length as there are pixels in the image (we work
        # with monochrome cameras, this needs to be adapted if someone uses color). The details of the array and desired
        # shape are stored in a process dict to be available for the creation of an image_port.
        shared_array = Array(array_type, shape[0] * shape[1])

        camera_dict = initial_dict.copy()
        camera_dict['shape'] = shape
        camera_dict['shared_array_type'] = array_type
        camera_dict['shared_array'] = shared_array

        return camera_dict

    def get_camera_by_index(self, index):
        # return a pylon.InstantCamera-object based on the given index. Index must be in range and has to be checked by
        # calling TlFactory.EnumerateDevices() to be sure that the camera exists
        TlFactory = pylon.TlFactory.GetInstance()
        available_devices = TlFactory.EnumerateDevices()
        assigned_camera = TlFactory.CreateDevice(available_devices[index])
        camera = pylon.InstantCamera(assigned_camera)

        return camera

    def run_setup(self):
        # these values have to be set after the process starts, because they are too complex for serialization.
        self.camera = self.get_camera_by_index(self.camera_dict['assigned_camera_index'])
        # open the assigned camera and give it its defined settings
        self.camera.Open()
        pylon.FeaturePersistence.Load(self.camera_dict['settings_path'], self.camera.GetNodeMap())

        # assign the ImageEventHandler subclass above to process and record frames.
        self.image_event_handler = BaslerImageHandler(self)
        self.camera.RegisterImageEventHandler(self.image_event_handler, pylon.RegistrationMode_ReplaceAll,
                                              pylon.Cleanup_Delete)

        # start the camera
        self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByInstantCamera)

        # set the process Event which tells other processes that it is ready
        self.ready.set()

    def run(self):
        # we need to run the setup of the camera and handler here, since they cant be built before the process starts
        self.run_setup()

        while self.alive:
            # while the process is alive, check every 50ms for new orders. Image processing and recording is handled by
            # the ImageEventHandler above.
            time.sleep(0.05)
            if self.pipe.poll():
                message = self.pipe.recv()
                print(message)
                if message == 'no_trigger':
                    self.set_camera_mode('no_trigger')
                elif message == 'hw_trigger':
                    self.set_camera_mode('hw_trigger')

        # Once the process is marked as not alive anymore, check if there is a remaining saving_process to wait for.
        if self.saving_process and self.saving_process.alive():
            self.saving_process.join()

        # finally tell the camera to stop grabbing and deactivate it (so that it is available to other processes again).
        self.camera.StopGrabbing()
        self.camera.Close()

    def get_camera_width(self, camera):
        # Calculate the camera sensor width by setting the x-offset to zero, checking the width, then resetting the
        # x-offset. This is necessary because basler cameras display the actual width + x-offset in the Width-node.
        x_offset = camera.OffsetX.GetValue()
        camera.OffsetX.SetValue(0)
        camera_width = camera.Width.Max
        camera.OffsetX.SetValue(x_offset)

        return camera_width

    def get_camera_height(self, camera):
        # Calculate the camera sensor height by setting the y-offset to zero, checking the height, then resetting the
        # y-offset. This is necessary because basler cameras display the actual height + y-offset in the Height-node.
        y_offset = camera.OffsetY.GetValue()
        camera.OffsetY.SetValue(0)
        camera_height = camera.Height.Max
        camera.OffsetY.SetValue(y_offset)

        return camera_height

    def set_camera_mode(self, mode):
        # Set the trigger mode to either have a constant feed or wait for a hardware trigger.
        if mode == 'hw_trigger':
            self.camera.TriggerMode.SetValue('On')
        elif mode == 'no_trigger':
            self.camera.TriggerMode.SetValue('Off')
        else:
            print(f'Unknown mode: {mode}')

    def set_recording(self, value):
        # function used to tell the assigned image_event_handler to start or stop recording. Only boolean values
        self.image_event_handler.set_recording(value)

    def stop_process(self):
        # used to tell this process to stop. Will wait for any running saving_processes before actually stopping
        self.alive = False

    def save_buffer(self, saving_location, fps):
        # tells the image_event_handler to return its buffer (and reset it), then give that buffer to a saving_process
        # for saving to the given location at the given fps. Wait for any other saving_processes before starting a new
        # one.
        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.join()

        self.saving_process = VideoSaveProcess(saving_location, fps, self.image_event_handler.return_buffer())
        self.saving_process.start()

    def get_image_port(self):
        # return a numpy array which is fed by the shared array, which means that outside processes can receive a
        # live-feed of the captured frames via this object.
        shared_array = self.camera_dict['shared_array']
        shape = self.camera_dict['shape']
        array_type = self.camera_dict['shared_array_type']

        return np.frombuffer(shared_array.get_obj(), array_type).reshape(shape)


if __name__ == '__main__':
    process_dict = {}
    process_dict['name'] = 'bla'
    process_dict['assigned_camera_index'] = 1
    process_dict['settings_path'] = '../Camera_Settings.pfs'

    (control_pipe, process_pipe) = Pipe()

    test = BaslerCameraProcess(process_dict, process_pipe)
    test.daemon = True
    test.start()

    test.ready.wait()

    output_port = test.get_image_port()

    print('go')
    time.sleep(1)

    control_pipe.send('no_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    control_pipe.send('hw_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    control_pipe.send('no_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    print('end')

