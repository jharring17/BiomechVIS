import plotly.express as px
import plotly.graph_objects as go
import scipy.io as sio
import numpy as np
import pandas as pd
import sys


#TODO color groups more distinctly 
#want the df to hold group names instead of a numerical id for the group names
#TODO the animation to be faster or at least adjustable
#TODO want a bar for the frame number
#TODO plot axis
# note we can use the add trace thing to make it so you can click to show points/groups and lines

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

    # add TBCM to points
    # df = pd.DataFrame(TBCM)
    # df.columns = ['X', 'Y', 'Z']
    # points['TBCM'] = df
    #final_points['TBCM'] = TBCM

    # TODO update this once we have a set idea of how we will draw lines and vectors
    # information for lines and vectors

    # do same for TBCMVeloc to points
    # df = pd.DataFrame(TBCMVeloc)
    # df.columns = ['X', 'Y', 'Z']
    # points['TBCMVeloc'] = df
    #final_points['TBCMVeloc'] = TBCMVeloc

    # add points for AnatAx to invis points 
    # structure is key is name points to x,y,z dicts 
    axes = {}
    a = ['X', 'Y', 'Z']
    for ax in AnatAx:
        com = COMs[ax]
        temp = {}
        for i, line in enumerate(AnatAx[ax]): #x line then y then z
            x = np.atleast_2d(line[0]).T*.1 + np.atleast_2d(com[:, 0]).T 
            y = np.atleast_2d(line[1]).T*.1 + np.atleast_2d(com[:, 1]).T 
            z = np.atleast_2d(line[2]).T*.1 + np.atleast_2d(com[:, 2]).T 
            temp[a[i]] = np.append(np.append(x, y, 1), z, 1)
        axes[ax] = temp

    return final_points, COMs, axes

def filter_points_to_draw(points, COMs, p_filter=[]):
    '''Takes in all points and filters out those in the filter
    Returns one df list.  Each frame is a df at its index
    Returns a list of names for each point in order they are listed in df'''
    frames = []
    labels = []
    #add mocap points
    for point_name in points:
        if point_name not in p_filter:
            for i, point in enumerate(points[point_name]):
                if len(frames) <= i:
                    frames.append([])
                frames[i].append(point)
            labels.append(point_name)

    #add COM points
    for point_name in COMs:
        if point_name not in p_filter:
            for i, point in enumerate(COMs[point_name]):
                if len(frames) <= i:
                    frames.append([])
                frames[i].append(point)
            labels.append(point_name)

    dfs = []
    for frame in frames:
        df = pd.DataFrame(frame)
        df.columns = ['X', 'Y', 'Z', 'Segment_ID']
        dfs.append(df)

    return dfs, labels

def filter_axis_to_draw(axis, a_filer=[]):
    '''Puts the axis into the dfs setup so they can be plotted invisibily'''
    frames = []
    for com_name in axis:
        if com_name not in a_filer:
            for dir in axis[com_name]:
                for i, point in enumerate(axis[com_name][dir]):
                    if len(frames) <= i:
                        frames.append([])
                    frames[i].append(point)
            
    frames = np.array(frames)
    dfs = []
    for frame in frames:
        df = pd.DataFrame(frame)
        df.columns = ['X', 'Y', 'Z']
        dfs.append(df)

    return dfs

def draw_anat_ax(plot, axes, COMs):
    '''Draws the lines for each anat ax starting from its corresponding COM'''
    #TODO see if this can be done in one draw_line call (not sure if an array of colors is possible)
    froms = []
    tos = []
    for name in COMs:
        froms.append(COMs[name])
        tos.append(axes[name]['X'])
    draw_line(plot, froms, tos, 'red', name='AnatAx X')

    tos = []
    for name in COMs:    
        tos.append(axes[name]['Y'])
    draw_line(plot, froms, tos, 'green', name='AnatAx Y')

    tos = []
    for name in COMs:
        tos.append(axes[name]['Z'])
    draw_line(plot, froms, tos, 'blue', name='AnatAx Z')


    return plot


def base_plot(dfs, labels, invis_dfs):
    '''Takes dfs and labels and returns the plot
    invis_dfs is the points to plot but not show (used for axis and vectors)
    Each index in dfs is a frame each point in dfs[x] is labeled in order by labels
    returns the plot object'''
    #info for the axis scaling
    x_min = -5
    x_max = 5
    y_min = -5
    y_max = 5
    z_min = 0
    z_max = 5
    scene_scaling = dict(xaxis = dict(range=[x_min, x_max], autorange=False),
                        yaxis = dict(range=[y_min, y_max], autorange=False),
                        zaxis = dict(range=[z_min, z_max], autorange=False),
                        aspectmode='cube')
    #the figure (full library)
    main_plot = go.Figure(
        data=[go.Scatter3d( x=dfs[0]['X'],
                            y=dfs[0]['Y'], 
                            z=dfs[0]['Z'],
                            mode='markers', #gets rid of line connecting all points
                            marker={'color':dfs[0]['Segment_ID'], 'size': 5},
                            hovertext= labels
                            ),
            go.Scatter3d(   x=invis_dfs[0]['X'],
                            y=invis_dfs[0]['Y'], 
                            z=invis_dfs[0]['Z'],
                            marker=dict(size=0, opacity=0), #makes them invis
                            mode='markers', #gets rid of line connecting all points
                            ), #just for frame 1
        ],
        layout=go.Layout(width=1600, height=800, #TODO dynamically set plot size
                        scene = scene_scaling,
                        title="Sample", #TODO change plot title
                        #slider= #TODO implement the frame slider
                        updatemenus=[dict(type="buttons",
                                            buttons=[dict(label="Play",
                                                        method="animate",
                                                        args=[None, {"fromcurrent": True, "frame": {"duration": 100, 'redraw': True}, "transition": {"duration": 0}}]), #TODO verify this controls the speed https://plotly.com/javascript/animations/
                                                    dict(label='Pause',
                                                        method="animate",
                                                        args=[[None], {"mode": "immediate"}]),
                                                    dict(label="Restart",
                                                        method="animate",
                                                        args=[None, {"frame": {"duration": 100, 'redraw': True}, "mode": 'immediate',}]),
                                                    ])]
        ),
        frames=[go.Frame(
                data= [go.Scatter3d(
                            x=dfs[i]['X'],
                            y=dfs[i]['Y'], 
                            z=dfs[i]['Z'], 
                            mode='markers', #gets rid of line connecting all points
                            marker={'color':dfs[i]['Segment_ID'],  'size': 5},
                            connectgaps=False, #TODO ask what we should do in this case.  Currently this stops the filling in of blanks/NaNs
                            hovertext = labels
                            ),
                        go.Scatter3d(
                            x=invis_dfs[i]['X'],
                            y=invis_dfs[i]['Y'], 
                            z=invis_dfs[i]['Z'], 
                            marker=dict(size=0, opacity=0), #makes them invis
                            mode='markers', #gets rid of line connecting all points
                            connectgaps=False, 
                            ),
                            ])
                for i in range(len(dfs))] #https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html
    )

    return main_plot

def draw_line(plot, froms, tos, cs='red', name='lines'):
    '''Add a line in all frames of plot from froms[x] to tos[x]'''

    #point list is [from, to, None] in a loop
    frames = []
    for n in range(len(froms[0])): #for every frame
        x = []
        y = []
        z = []
        frame = []
        for i in range(len(froms)): #for every set of points 
            x.append(froms[i][n][0])
            x.append(tos[i][n][0])
            y.append(froms[i][n][1])
            y.append(tos[i][n][1])
            z.append(froms[i][n][2])
            z.append(tos[i][n][2])
            x.append(None)
            y.append(None)
            z.append(None)
        frame.append(x)
        frame.append(y)
        frame.append(z)
        frames.append(frame)

    plot.add_trace(go.Scatter3d(
        x=frames[0][0],
        y=frames[0][1],
        z=frames[0][2],
        mode='lines', line=dict(color=cs), name=name
    ))

    #one pass per frame for all lines O(n) where n = #frames
    for i, frame in enumerate(plot.frames):
        temp = list(frame.data)
        temp.append(go.Scatter3d(x=frames[i][0], y=frames[i][1], z=frames[i][2], mode='lines', line=dict(color=cs)))
        frame.data = temp

    return plot

def draw_timeseries(point, point_name=''):
    '''Shows x, y and z timeseries for a given point'''
    x = point[:,0].T
    y = point[:,1].T
    z = point[:,2].T
    time = list(range(len(z)))

    fig_x = go.Figure(data=go.Scatter(x=time, y=x, mode='markers+lines'), layout=go.Layout(title=f'Point {point_name} X over time', xaxis_title='Frame', yaxis_title='X'))
    fig_y = go.Figure(data=go.Scatter(x=time, y=y, mode='markers+lines'), layout=go.Layout(title=f'Point {point_name} Y over time', xaxis_title='Frame', yaxis_title='Y'))
    fig_z = go.Figure(data=go.Scatter(x=time, y=z, mode='markers+lines'), layout=go.Layout(title=f'Point {point_name} Z over time', xaxis_title='Frame', yaxis_title='Z'))

    fig_x.show()
    fig_y.show()
    fig_z.show()






points, COMs, axes = read_Mitchell_data()

draw_timeseries(points['LHM2'], 'LHM2')


dfs, labels = filter_points_to_draw(points, COMs)
invis_dfs = filter_axis_to_draw(axes)
main_plot = base_plot(dfs, labels, invis_dfs)
main_plot = draw_line(main_plot, [COMs['PELVIS'], points['LHM2']], [COMs['TORSO'], points['RHM2']])
main_plot = draw_anat_ax(main_plot, axes, COMs)


main_plot.show()