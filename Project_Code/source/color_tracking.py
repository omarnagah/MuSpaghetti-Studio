#importing modules
import math
from collections import OrderedDict


def music_main(music_data):
    pygame.init()
    music_main.wave_obj = OrderedDict()
    music_main.sound_channel = {}
    music_main.image_obj = OrderedDict()
    image_position = [(100, 130), (450, 130) , (100, 400), (450, 400)]
    for i, (track, position) in enumerate(zip(music_data, image_position)):
        pathTail = os.path.split(track[0])[1]
        soundName = os.path.splitext(pathTail)[0]
        soundName += '@'+str(i+1)
        pathTail = os.path.split(track[1])[1]
        imageName = os.path.splitext(pathTail)[0]
        imageName += '@'+str(i+1)
        music_main.wave_obj[soundName] = []
        music_main.image_obj[imageName] = []
        for j, data in enumerate(track):
            if j == 0:
                music_main.wave_obj[soundName].append(pygame.mixer.Sound(data))
                music_main.wave_obj[soundName][0].set_volume(1)
                music_main.sound_channel[soundName] = pygame.mixer.Channel(i)
            elif j == 1:
                dim = (100, 100)
                resized = cv2.resize(cv2.imread(data), dim, interpolation = cv2.INTER_AREA)
                music_main.image_obj[imageName].extend((position, resized))
            else:
                music_main.wave_obj[soundName].extend((data, True))
                
    music_main.frameCount = 0
    music_main.timeStart = time.time()
    music_main.b1 = (0,0)
    music_main.b2 = (0,0)
    music_main.currentBlueVelocity = 0
    music_main.r1 = (0,0)
    music_main.r2 = (0,0)
    music_main.currentRedVelocity = 0
    
    music_main.booli  = [False for i in range(4)]
    music_main.drums = [None for i in range(4)]
        
    def drawEllipse(contours, text):
        if(contours == None or len(contours) == 0):
            return ((-100,-100), None)
        c = max(contours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        if(cv2.contourArea(c) < 500):
            return ((-100,-100), None)
        ellipse = cv2.fitEllipse(c)
        
        blank = np.zeros(music_processing.img.shape[0:2])
        ellipseImage = cv2.ellipse(blank, ellipse, (255, 255, 255), -2)
    
        M = cv2.moments(c)
        if M["m00"] == 0:
            return
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        
        globals.write_lock.acquire()
        cv2.ellipse(globals.main_frame, ellipse, (0,0,0), 2)
        if radius > 10 and radius<100:
            # draw the ellipse and centroid on the frame,
            # then update the list of tracked points
            # cv2.circle(img, (int(x), int(y)), int(radius),(0, 0, 0), 2)
            cv2.circle(globals.main_frame, center, 3, (0, 0, 255), -1)
            cv2.putText(globals.main_frame,text, (center[0]+10,center[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 0, 0),2)
            cv2.putText(globals.main_frame,"("+str(center[0])+","+str(center[1])+")", (center[0]+10,center[1]+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 0, 0),1)
        globals.write_lock.release()

        return (center, ellipseImage)
    
    def detectCollision(imgA, imgB, velocity, touching, name):
        mA = cv2.moments(imgA, False)
        mB = cv2.moments(imgB, False)
        blank = np.zeros(music_processing.img.shape[0:2])
        if type(imgA) == type(None) or type(imgB) == type(None):
            return
        intersection = cv2.bitwise_and(imgA, imgB)
        area = cv2.countNonZero(intersection)
        if area < 20:
            touching = False
        if area > 100 and not touching:
            if int(mA["m01"] / mA["m00"])< int(mB["m01"] / mB["m00"]):
                if velocity > 10:
                    if music_main.wave_obj[name][1]==0:
                        music_main.sound_channel[name].play(music_main.wave_obj[name][0])
                    elif music_main.wave_obj[name][1]==1:
                        if not (music_main.wave_obj[name][2] or music_main.sound_channel[name].get_busy()):
                            music_main.wave_obj[name][2] = True
                        if music_main.wave_obj[name][2]:
                            if music_main.sound_channel[name].get_busy():
                                music_main.sound_channel[name].unpause()
                            else:
                                music_main.sound_channel[name].play(music_main.wave_obj[name][0])
                        else:
                            music_main.sound_channel[name].pause()
                    elif music_main.wave_obj[name][1]==2:
                        if music_main.wave_obj[name][2]:
                            music_main.sound_channel[name].play(music_main.wave_obj[name][0], -1)
                        else:
                            music_main.sound_channel[name].stop()
                    music_main.wave_obj[name][2] = not music_main.wave_obj[name][2]
            touching = True
        
    def newDrum_picture(pos, name, resized):
        alpha =0.2
        h,w,c = resized.shape
        sub=(w/2,h/2)
        start = tuple(map(lambda i, j:int (i - j), pos, sub))
        end = tuple(map(lambda i, j:int (i + j), pos, sub))
        blank = np.zeros(music_processing.img.shape[0:2])
        drum_image = cv2.rectangle(blank.copy(), start, end, (255,255,255), -5) 
        x,y = start
        globals.write_lock.acquire()
        test = globals.main_frame
        added_image = cv2.addWeighted(test[y:y+h, x:x+w,:],alpha,resized,1-alpha,0)
        test[y:y+h, x:x+w] = added_image
        globals.write_lock.release()
        return (name, drum_image)
        
    def music_processing(img):
        now = time.time()
        fps = music_main.frameCount / (now - music_main.timeStart)
        music_main.frameCount += 1
        
        music_processing.img = img
        
        globals.write_lock.acquire()
        cv2.putText(globals.main_frame,"FPS: %.2f" % (fps),(10,220),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        globals.write_lock.release()
        
        #converting frame(img i.e BGR) to HSV (hue-saturation-value)
        hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

        ###############################red[168 204 132] [188 224 212]
        #test######blue[ 95 209  82] [115 229 162] [ 96 191  79] [116 211 159]
        red_lower=np.array([ 0, 222 , 55] ,np.uint8)
        red_upper=np.array([ 12 , 251 , 140],np.uint8)
        blue_lower=np.array([95, 191 , 80],np.uint8)
        blue_upper=np.array([115 ,229 ,162],np.uint8)
        ###############################

        #finding the range of red,blue color in the image
        red1=cv2.inRange(hsv, red_lower, red_upper)
        blue=cv2.inRange(hsv,blue_lower,blue_upper)
        red_lower=np.array([ 168 , 204 , 132] ,np.uint8)
        red_upper=np.array([ 189 , 230 , 212],np.uint8)
        red2=cv2.inRange(hsv, red_lower, red_upper)
        red = red1 + red2
        #Morphological transformation, Dilation
        kernal = np.ones((5 ,5), "uint8")

        red=cv2.dilate(red, kernal)
        res=cv2.bitwise_and(img, img, mask = red)

        blue=cv2.dilate(blue,kernal)
        res1=cv2.bitwise_and(img, img, mask = blue)


        #Tracking the Red Color
        (contours,hierarchy)=cv2.findContours(red,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        (redCenter, redEllipse) = drawEllipse(contours, "Red")
        # cv2.drawContours(img, contours, -1 , (0,0,255), 2)


        #Tracking the Blue Color
        (contours,hierarchy)=cv2.findContours(blue,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        # cv2.drawContours(img, contours, -1 , (255,0,0), 2)
        (blueCenter, blueEllipse) = drawEllipse(contours, "Blue")

        music_main.b1 = music_main.b2
        music_main.b2 = blueCenter
        bDelta = math.sqrt((music_main.b2[0] - music_main.b1[0])**2 + (music_main.b2[1] - music_main.b1[1])**2)
        bVelocity = bDelta * fps / 100
        globals.write_lock.acquire()
        if (bVelocity - music_main.currentBlueVelocity) > 10:
            cv2.putText(globals.main_frame,str(int(bVelocity)),(10, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)
        else:
            cv2.putText(globals.main_frame,str(int(music_main.currentBlueVelocity)),(10, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)
        globals.write_lock.release()
        music_main.currentBlueVelocity = bVelocity

        music_main.r1 = music_main.r2
        music_main.r2 = redCenter
        rDelta = math.sqrt((music_main.r2[0] - music_main.r1[0])**2 + (music_main.r2[1] - music_main.r1[1])**2)
        rVelocity = rDelta * fps / 100
        globals.write_lock.acquire()
        if (rVelocity - music_main.currentRedVelocity) > 10:
            cv2.putText(globals.main_frame,str(int(rVelocity)),(70, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        else:
            cv2.putText(globals.main_frame,str(int(music_main.currentRedVelocity)),(70, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        globals.write_lock.release()
        music_main.currentRedVelocity = rVelocity
        
        #Add the drums
        for i, (keyName, data) in enumerate(zip(music_main.wave_obj.keys(), music_main.image_obj.values())):
            music_main.drums[i] = newDrum_picture(data[0], keyName, data[1])

        for i in range(len(music_main.drums)):
            music_main.booli[i] = detectCollision(blueEllipse, music_main.drums[i][1], music_main.currentBlueVelocity, music_main.booli[i], music_main.drums[i][0])
            music_main.booli[i] = detectCollision(redEllipse, music_main.drums[i][1], music_main.currentRedVelocity, music_main.booli[i], music_main.drums[i][0])
 
    return music_processing
    
    
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
    music_data = [['sound_tracks/snare.wav', 'images/drum_1.jpg', 1],
                  ['sound_tracks/hi_hat.wav', 'images/drum_2.jpg', 2],
                  ['sound_tracks/O-Hi-Hat.wav', 'images/drum_3.jpg', 0],
                  ['sound_tracks/output.wav', 'images/drum_4.jpg', 0]]
    music_processing = music_main(music_data)
    while(camera.isOpened()):
        # get the current frame
        (grabbed, globals.main_frame) = camera.read()
        # resize the frame
        globals.main_frame = imutils.resize(globals.main_frame, width=700)
        # flip the frame so that it is not the mirror view
        globals.main_frame = cv2.flip(globals.main_frame, 1)
        # start sign processing
        music_processing(globals.main_frame.copy())
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
    
