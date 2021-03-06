#------------------------------------------------------------
# SEGMENT, RECOGNIZE and COUNT fingers from a video sequence
#------------------------------------------------------------

# organize imports
from sklearn.metrics import pairwise
from threading import Thread
import wave
import pyaudio

# global variables
bg = None

#--------------------------------------------------
# To find the running average over the background
#--------------------------------------------------
def run_avg(image, accumWeight):
    global bg
    # initialize the background
    if bg is None:
        bg = image.copy().astype("float")
        return

    # compute weighted average, accumulate it and update the background
    cv2.accumulateWeighted(image, bg, accumWeight)

#---------------------------------------------
# To segment the region of hand in the image
#---------------------------------------------
def segment(image, threshold=25):
    global bg
    # find the absolute difference between background and current frame
    diff = cv2.absdiff(bg.astype("uint8"), image)

    # threshold the diff image so that we get the foreground
    thresholded = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)[1]

    # get the contours in the thresholded image
    ( cnts, _) = cv2.findContours(thresholded.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # return None, if no contours detected
    if len(cnts) == 0:
        return
    else:
        # based on contour area, get the maximum contour which is the hand
        segmented = max(cnts, key=cv2.contourArea)
        return (thresholded, segmented)

#--------------------------------------------------------------
# To count the number of fingers in the segmented hand region
#--------------------------------------------------------------
def count(thresholded, segmented):
    # find the convex hull of the segmented hand region
    chull = cv2.convexHull(segmented)

    # find the most extreme points in the convex hull
    extreme_top    = tuple(chull[chull[:, :, 1].argmin()][0])
    extreme_bottom = tuple(chull[chull[:, :, 1].argmax()][0])
    extreme_left   = tuple(chull[chull[:, :, 0].argmin()][0])
    extreme_right  = tuple(chull[chull[:, :, 0].argmax()][0])

    # find the center of the palm
    cX = int((extreme_left[0] + extreme_right[0]) / 2)
    cY = int((extreme_top[1] + extreme_bottom[1]) / 2)

    # find the maximum euclidean distance between the center of the palm
    # and the most extreme points of the convex hull
    distance = pairwise.euclidean_distances([(cX, cY)], Y=[extreme_left, extreme_right, extreme_top, extreme_bottom])[0]
    maximum_distance = distance[distance.argmax()]

    # calculate the radius of the circle with 80% of the max euclidean distance obtained
    radius = int(0.8 * maximum_distance)

    # find the circumference of the circle
    circumference = (2 * np.pi * radius)

    # take out the circular region of interest which has 
    # the palm and the fingers
    circular_roi = np.zeros(thresholded.shape[:2], dtype="uint8")
	
    # draw the circular ROI
    cv2.circle(circular_roi, (cX, cY), radius, 255, 1)

    # take bit-wise AND between thresholded hand using the circular ROI as the mask
    # which gives the cuts obtained using mask on the thresholded hand image
    circular_roi = cv2.bitwise_and(thresholded, thresholded, mask=circular_roi)

    # compute the contours in the circular ROI
    ( cnts, _) = cv2.findContours(circular_roi.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    # initalize the finger count
    count = 0

    # loop through the contours found
    for c in cnts:
        # compute the bounding box of the contour
        (x, y, w, h) = cv2.boundingRect(c)

        # increment the count of fingers only if -
        # 1. The contour region is not the wrist (bottom area)
        # 2. The number of points along the contour does not exceed
        #     25% of the circumference of the circular ROI
        if ((cY + (cY * 0.25)) > (y + h)) and ((circumference * 0.25) > c.shape[0]):
            count += 1

    return count
    
def start_recording(filename):
    chunk = 1024  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    channels = 2    # Two input channels
    dev_index = None    # Default device index
    if sign_main.input_device is not None:
        channels = sign_main.input_device['maxInputChannels']  # number of input channels
        dev_index = sign_main.input_device['index']  # input audio device index
    fs = 44100  # Record at 44100 samples per second

    p = pyaudio.PyAudio()  # Create an interface to PortAudio

    print('Recording')

    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True,
                    input_device_index=dev_index)

    frames = []  # Initialize array to store frames

    # Store data in chunks for 3 seconds
    while(sign_main.flag):
        data = stream.read(chunk)
        frames.append(data)

    # Stop and close the stream 
    stream.stop_stream()
    stream.close()
    # Terminate the PortAudio interface
    p.terminate()

    print('Finished recording')
    
    if not sign_main.canceled:
        if os.path.isfile(filename):
            os.remove(filename)
        # Save the recorded data as a WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))
        wf.close()

def sign_main(file_path, device_name, background_music):
    pygame.init()
    sign_main.background_music = background_music
    if background_music is not None:
        pygame.mixer.music.load(background_music)
        pygame.mixer.music.set_volume(0.7)
        
    sign_main.input_device = None
    if device_name is not None:
        pyaudio_instance = pyaudio.PyAudio()
        for i in range(pyaudio_instance.get_device_count()):
            dev = pyaudio_instance.get_device_info_by_index(i)
            if (dev['name'] == device_name and dev['hostApi'] == 0):
                sign_main.input_device = dev;
            
    # recording file path
    sign_main.file_path = file_path
    
    # initialize accumulated weight
    sign_main.accumWeight = 0.5

    # region of interest (ROI) coordinates
    sign_main.top, sign_main.right, sign_main.bottom, sign_main.left = 190, 550, 360, 680

    # initialize num of frames
    sign_main.num_frames = 0

    # calibration indicator
    calibrated = False
    sign_main.i=0
    sign_main.j=0
    sign_main.flag=False
    sign_main.recorded=False
    sign_main.canceled=False
    
    # keep looping, until interrupted
    def sign_processing(frame):

        # get the height and width of the frame
        (height, width) = frame.shape[:2]

        # get the ROI
        roi = frame[sign_main.top:sign_main.bottom, sign_main.right:sign_main.left]

        # convert the roi to grayscale and blur it
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # to get the background, keep looking till a threshold is reached
        # so that our weighted average model gets calibrated
        if sign_main.num_frames < 30:
            run_avg(gray, sign_main.accumWeight)
            globals.write_lock.acquire()
            cv2.putText(globals.main_frame, "Calibrating", (250, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            globals.write_lock.release()
            if sign_main.num_frames == 1:
                print("[STATUS] please wait! calibrating...")
            elif sign_main.num_frames == 29:
                print("[STATUS] calibration successfull...")
        else:
            # segment the hand region
            hand = segment(gray)

            # check whether hand region is segmented
            if hand is not None:
                # if yes, unpack the thresholded image and
                # segmented region
                (thresholded, segmented) = hand

                # draw the segmented region and display the frame
                globals.write_lock.acquire()
                cv2.drawContours(globals.main_frame, [segmented + (sign_main.right, sign_main.top)], -1, (0, 0, 255))
                globals.write_lock.release()
                
                # count the number of fingers
                fingers = count(thresholded, segmented)

                if fingers==1 and  (not sign_main.flag):
                    sign_main.i=sign_main.i+1
                    if sign_main.i ==25:
                        print ("start")
                        sign_main.flag=True
                        sign_main.i=0
                        sign_processing.recording_thread = Thread(target=start_recording, args=(sign_main.file_path,), daemon=True)
                        sign_processing.recording_thread.start()
                        if sign_main.background_music is not None:
                            pygame.mixer.music.play(-1)
                        #record func

                if fingers==2 and sign_main.flag:
                    sign_main.j=sign_main.j+1
                    if sign_main.j ==25:
                        print ("stop")
                        sign_main.flag=False
                        sign_main.j=0
                        if sign_main.background_music is not None:
                            pygame.mixer.music.stop()
                        sign_processing.recording_thread.join()
                        sign_main.recorded=True
                        #stop function
                
                globals.write_lock.acquire()
                cv2.putText(globals.main_frame, str(fingers), (150, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                globals.write_lock.release()                
                # show the thresholded image
                #cv2.imshow("Thresholded", thresholded)

        # draw the segmented hand
        globals.write_lock.acquire()
        cv2.rectangle(globals.main_frame, (sign_main.left, sign_main.top), (sign_main.right, sign_main.bottom), (0,255,0), 2)
        if sign_main.flag:
            cv2.putText(globals.main_frame, "Recording", (250, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        globals.write_lock.release()
        
        # increment the number of frames
        sign_main.num_frames += 1
        
    return sign_processing
            
#-----------------
# MAIN FUNCTION
#-----------------
if __name__ == "__main__":
    import globals
    from sharedLibs import *
    # initialize global variables
    globals.initialize()
    # get the reference to the webcam
    camera=cv2.VideoCapture(0)
    # start a named window with cnotrollable size
    window_name = "music_studio"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # run main function
    filename = "records/output.wav"
    background_music = "sound_tracks/ana_gad3.wav"
    device_name = "Stereo Mix (Realtek(R) Audio)"
    sign_processing = sign_main(filename, device_name, background_music)
    while(camera.isOpened()):
        # get the current frame
        (grabbed, globals.main_frame) = camera.read()
        # resize the frame
        globals.main_frame = imutils.resize(globals.main_frame, width=700)
        # flip the frame so that it is not the mirror view
        globals.main_frame = cv2.flip(globals.main_frame, 1)
        # start sign processing
        sign_processing(globals.main_frame.copy())
        # display the global frame after processing
        cv2.imshow(window_name, globals.main_frame)
        # observe the keypress by the user
        keypress = cv2.waitKey(1) & 0xFF
        # if the user pressed "q", then stop looping
        if keypress == ord("q"):
            break    
    # free up memory
    camera.release()
    cv2.destroyAllWindows()
else:
    from source import globals
    from source.sharedLibs import *
    