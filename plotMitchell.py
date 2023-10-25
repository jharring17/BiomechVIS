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
#TODO plot lines
#TODO cleaner data read for new format
#TODO plot axis
#TODO plot COM
#TODO add color back

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

    #make COM dict the same as above
    #TODO maybe add a distinguishing tag so these can be seen to be COMs and colored accordingly
    for name in SegCOM:
        points = SegCOM[name]
        tag = np.full((points.shape[0], 1), 0) #0 tag for COMs
        points = np.append(points, tag, 1)
        final_points[f'{name}_COM'] = points

    for ax in AnatAx:
        print(AnatAx[ax].shape)

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

    # add points for AnatAx to points
    # for ax in AnatAx:
    #     points = AnatAx[ax]
    #     df = pd.DataFrame(points)
    #     df.columns = ['X', 'Y', 'Z']
    #     points[name] = df

    return final_points

def filter_points_to_draw(points, p_filter=[]):
    '''Takes in all points and filters out those in the filter
    Returns one df list.  Each frame is a df at its index
    Returns a list of names for each point in order they are listed in df'''
    frames = []
    labels = []
    for point_name in points:
        if point_name not in p_filter:
            for i, point in enumerate(points[point_name]):
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

#Choices: working sample -> 'SampleData.mat' , one that is being worked on -> 'Mitchell_MocapData_Nairobi21.mat'

points = read_Mitchell_data()
dfs, labels = filter_points_to_draw(points)


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
                        ) #just for frame 1
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
                        x=df['X'],
                        y=df['Y'], 
                        z=df['Z'], 
                        mode='markers', #gets rid of line connecting all points
                        marker={'color':df['Segment_ID'],  'size': 5},
                        connectgaps=False, #TODO ask what we should do in this case.  Currently this stops the filling in of blanks/NaNs
                        hovertext = labels
                        )])
            for df in dfs] #https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html
)



main_plot.show()