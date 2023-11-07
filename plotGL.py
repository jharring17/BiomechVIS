import pygame
from pygame.locals import *
import pygame.font
from OpenGL.GLUT import glutStrokeCharacter, GLUT_STROKE_ROMAN
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import scipy.io as sio
import numpy as np
import pandas as pd
import sys

def draw_axes():
    # X-axis (Red)
    glColor3f(1, 0, 0)
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(1, 0, 0)
    glEnd()
    # Y-axis (Green)
    glColor3f(0, 1, 0)
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 1, 0)
    glEnd()
    # Z-axis (Blue)
    glColor3f(0, 0, 1)
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 1)
    glEnd()

def plot_points(points, current_frame):
    glBegin(GL_POINTS)
    for point, frame in points:
        if frame == current_frame:
            glVertex3fv(point)
    glEnd()

def load_from_mat(filename=None, data={}, loaded=None):
    '''Turn .mat file to nested dict of all values
    Pulled from https://stackoverflow.com/questions/62995712/extracting-mat-files-with-structs-into-python'''
    if filename:
        vrs = sio.whosmat(filename)
        #name = vrs[0][0]
        loaded = sio.loadmat(filename,struct_as_record=True)
        loaded = loaded["Data"] #Data is labeled differently, so just specified data field - Nick
        
    whats_inside = loaded.dtype.fields
    fields = list(whats_inside.keys())
    for field in fields:
        if len(loaded[0,0][field].dtype) > 0: # it's a struct
            data[field] = {}
            data[field] = load_from_mat(data=data[field], loaded=loaded[0,0][field])
        else: # it's a variable
            data[field] = loaded[0,0][field]
    return data

def read_Mitchell_data():
    '''Read Mitchell data 
    Specified as a folder with hardcoded to contain exactly the five sample folders for now
    Folder path is sys.argv[1]
    Returns dictonary of COM dfs and dictonary of points dfs'''
    #TODO update to take general file names in given folder
    #Note: The data dict in load_from_math seems to carry over somehow? If I don't set it to {} Then SegCOM will change once we read MocapData for example - Gavin
    folder_path = sys.argv[1]
    # AnatAx => key = seg name, val = 3x3xN array for location so [frame][x_axis,y_axis,z_axis][x,y,z]
    AnatAx = load_from_mat(f'{folder_path}/Mitchell_AnatAx_Nairobi21.mat', {})
    #TBCMVeloc => need to read seperately.  It just has a data array which is Nx3 for locations
    TBCMVeloc = sio.loadmat(f'{folder_path}/Mitchell_TBCMVeloc_Nairobi21.mat', struct_as_record=True)['Data']
    #TBCM => need to read seperately.  It just has a data array which is Nx3 for locations 
    TBCM  = sio.loadmat(f'{folder_path}/Mitchell_TBCM_Nairobi21.mat', struct_as_record=True)['Data']
    # SegCOM => key = seg name, val = Nx3 array for location (only first value populated?)
    SegCOM = load_from_mat(f'{folder_path}/Mitchell_SegCOM_Nairobi21.mat', {})

    # MocapData => key = point name, val = Nx3 array for location
    MocapData = load_from_mat(f'{folder_path}/Mitchell_MocapData_Nairobi21.mat', {})

    #make dictonary of points dfs indexed by point name
    final_points = {}
    for i, name in enumerate(MocapData):
        points = MocapData[name]
        tag = np.full((points.shape[0], 1), i + 1) #id for later (eventually should be segment based rn its point based)
        points = np.append(points, tag, 1)
        final_points[name] = points

    #make COM dict 
    COMs = {}
    for name in SegCOM:
        points = SegCOM[name]
        tag = np.full((points.shape[0], 1), 0) #0 tag for COMs
        points = np.append(points, tag, 1)
        COMs[name] = points

    # add points for AnatAx to invis points 
    # structure is key is name points to x,y,z dicts 
    invis_points = {}
    for ax in AnatAx:
        temp = {}
        temp['X'] = AnatAx[ax][0].T
        temp['Y'] = AnatAx[ax][1].T
        temp['Z'] = AnatAx[ax][2].T
        invis_points[ax] = temp

    return final_points, COMs, invis_points

def handle_events(camera_z, paused):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Mouse wheel up
                camera_z += 0.1
            elif event.button == 5:  # Mouse wheel down
                camera_z -= 0.1
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:  # Spacebar toggles pause
                paused = not paused
    return camera_z, paused


def convert_read(points):
    output = []
    for name in points:
        plist = points[name]
        for i, elem in enumerate(plist):
            if isinstance(elem, np.ndarray):  # Check if point is a numpy array
                elem = elem.tolist()  # Convert numpy array to a Python list
            output.append((elem[:-1], i))
    return output

def draw_lines_between_points(lines, current_frame):
    glBegin(GL_LINES)
    for start_point, end_point, frame in lines:
        if frame == current_frame:
            glVertex3fv(start_point)
            glVertex3fv(end_point)
    glEnd()

def read_a_line(p1_list, p2_list):
    output = []
    for i in range(len(p1_list)):
        output.append([tuple(p1_list[i][:-1]), tuple(p2_list[i][:-1]), i])

    return output

def main():
    pygame.init()
    display = (1000, 800)
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -5)

    pitch = -90
    roll = 0
    yaw = 0
    camera_x = 0
    camera_y = 5
    camera_z = -1

    point_scale = 1

    points_dict, COMs, invis_points = read_Mitchell_data()
    points_to_plot = convert_read(points_dict)
    lines = []

    #every permutation ofa line
    for i, key1 in enumerate(points_dict):
        if i > 1:
            break
        for j, key2 in enumerate(points_dict):
            if j > 10:
                break
            lines += read_a_line(points_dict[key1], points_dict[key2])
        print(f'{i}/{len(points_dict)}')
    

    max_frames = max(frame for _, frame in points_to_plot)

    clock = pygame.time.Clock()

    current_frame = 1
    paused = False

    while True:  # Infinite loop to keep animating
        mouse_x, mouse_y = pygame.mouse.get_pos()
        camera_z, paused = handle_events(camera_z, paused)  # Handle mouse events

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

        keys = pygame.key.get_pressed()

        # Camera Controls
        if keys[pygame.K_w]:
            camera_z += 0.1
        if keys[pygame.K_s]:
            camera_z -= 0.1
        if keys[pygame.K_a]:
            camera_x += 0.1
        if keys[pygame.K_d]:
            camera_x -= 0.1
        if keys[pygame.K_q]:
            camera_y += 0.1
        if keys[pygame.K_e]:
            camera_y -= 0.1
        if keys[pygame.K_UP]:
            pitch += 1
        if keys[pygame.K_DOWN]:
            pitch -= 1
        if keys[pygame.K_LEFT]:
            yaw += 1
        if keys[pygame.K_RIGHT]:
            yaw -= 1
        if keys[pygame.K_z]:
            roll += 1
        if keys[pygame.K_c]:
            roll -= 1

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        glRotatef(pitch, 1, 0, 0)
        glRotatef(roll, 0, 0, 1)
        glRotatef(yaw, 0, 1, 0)
        glTranslatef(camera_x, camera_y, camera_z)
        glPointSize(point_scale)  # Set the point size to 5 (you can adjust this value as needed)
        plot_points(points_to_plot, current_frame)  # Plot points for the current frame
        draw_lines_between_points(lines, current_frame)  # Draw lines based on frame
        draw_axes()  # Draw the X, Y, Z axes
        glPopMatrix()
        pygame.display.flip()

        if not paused:
            print(current_frame)
            current_frame += 1

            if current_frame > max_frames:
                current_frame = 1  # Reset to the first frame when reaching the end

        clock.tick(200)  # Set the frame rate to 60 frames per second

if __name__ == "__main__":
    main()
