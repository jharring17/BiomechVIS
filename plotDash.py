import plotly.express as px
import plotly.graph_objects as go
import scipy.io as sio
import numpy as np
import pandas as pd
import sys
from dash import Dash, dcc, html, Input, Output, State, callback_context, MATCH, no_update, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
import os
import tkinter as tk
from tkinter import filedialog
from dash.exceptions import PreventUpdate

#TODO color groups more distinctly 
#want the df to hold group names instead of a numerical id for the group names
#TODO the animation to be faster or at least adjustable
#TODO want a bar for the frame number
#TODO plot axis
# note we can use the add trace thing to make it so you can click to show points/groups and lines
global numOf2dGraphs, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, selected_y_axis_point_2D, file_list_2D
numOf2dGraphs= 0
global newGraphNumOfLines
newGraphNumOfLines=1
global filesList
filesList = {}
filesList = {'AnatAx' : [], 'SegCOM': [], 
             'TBCM' : [], 'TBCMVeloc' : [],
             'MocapData' : []}

# Change each field to be an array; append to the array when adding fields 
# Wipe arrays clean when changing files from other thing
# Load mat will combine them, what will sci thing do?
# in load mat, jsut do it for each component of array, and merge the dicts; prob a method
# For TBCM and other thing, append array together 

def load_from_mat(filenames=None, data={}, loaded=None):
    '''Turn .mat file to nested dict of all values
    Pulled from https://stackoverflow.com/questions/62995712/extracting-mat-files-with-structs-into-python'''
    for filename in filenames:
        if filename:
            vrs = sio.whosmat(filename)
            #name = vrs[0][0]
            loaded = sio.loadmat(filename,struct_as_record=True)
            if 'Data' in loaded.keys():
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

def load_from_mat2(filenames):
    noDataInit = True
    for filename in filenames:
        fileData = sio.loadmat(filename, struct_as_record=True)['Data']
        if (noDataInit):
            data = fileData
            noDataInit = False
        else:
            data = np.concatenate((data, fileData)) #We dont care about order, just add em together
    return data

def read_Mitchell_data(framerate):
    '''Read Mitchell data 
    Specified as a folder with hardcoded to contain exactly the five sample folders for now
    Folder path is sys.argv[1]
    Returns dictonary of COM dfs and dictonary of points dfs'''
    #TODO update to take general file names in given folder
    #Note: The data dict in load_from_math seems to carry over somehow? If I don't set it to {} Then SegCOM will change once we read MocapData for example - Gavin
    #folder_path = sys.argv[1]

    files_2D = [{"label": "Mocap Data", "value": "Mocap"}]

    print(filesList)
    # AnatAx => key = seg name, val = 3x3xN array for location so [frame][x_axis,y_axis,z_axis][x,y,z]   
    if len(filesList['AnatAx']) == 0:
        AnatAx = {}
    else:
        AnatAx = load_from_mat(filesList['AnatAx'], {})
    #TBCMVeloc => need to read seperately.  It just has a data array which is Nx3 for locations
    if len(filesList['TBCMVeloc']) == 0:
        TBCMVeloc = []
    else:
        TBCMVeloc = load_from_mat2(filesList['TBCMVeloc'])
        files_2D.append({"label": "TBCMVeloc", "value": "TBCMVeloc"})

    #TBCM => need to read seperately.  It just has a data array which is Nx3 for locations 
    if len(filesList['TBCM']) == 0:
        TBCM = []
    else:
        TBCM  = load_from_mat2(filesList['TBCM'])
        files_2D.append({"label": "TBCM", "value": "TBCM"})
    # SegCOM => key = seg name, val = Nx3 array for location (only first value populated?)
    if len(filesList['SegCOM']) == 0:
        SegCOM = {}
    else:
        SegCOM = load_from_mat(filesList['SegCOM'], {})

    # MocapData => key = point name, val = Nx3 array for location
    MocapData = load_from_mat(filesList['MocapData'], {})

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

    vectors = {}
    #TODO change from hardcoded
    vectors['TBCM'] = [[], []]
    
    noVectors = False
    vectors['TBCM'][0] = TBCM
    if (len(TBCM) != 0 and len(TBCMVeloc) != 0):
        vectors['TBCM'][1] = TBCM + TBCMVeloc
        noVectors = True

    # add points for AnatAx to invis points 
    # structure is key is name points to x,y,z dicts 
    axes = {}
    a = ['X', 'Y', 'Z']
    for ax in AnatAx:
        com = COMs[ax]
        temp = {}
        for i, line in enumerate(AnatAx[ax]): #x line then y then z
            try:
                x = np.atleast_2d(line[0]).T*.1 + np.atleast_2d(com[:, 0]).T 
                y = np.atleast_2d(line[1]).T*.1 + np.atleast_2d(com[:, 1]).T 
                z = np.atleast_2d(line[2]).T*.1 + np.atleast_2d(com[:, 2]).T 
                temp[a[i]] = np.append(np.append(x, y, 1), z, 1)
            except:
                print("AnatAx Error")
        axes[ax] = temp

    
    undersampled_final_points = {key: value[::framerate] for key, value in final_points.items()}
    # Undersample COMs
    undersampled_COMs = {key: value[::framerate] for key, value in COMs.items()}
    # Undersample vectors
    if (noVectors):
        undersampled_vectors = {key: [value[0][::framerate], value[1][::framerate]] for key, value in vectors.items()}
    else:
        undersampled_vectors = {}
    # Undersample axes
    undersampled_axes = {}
    for ax, temp in axes.items():
        undersampled_axes[ax] = {coord: data[::framerate] for coord, data in temp.items()}

    all_points = final_points
    all_points['TBCM'] = TBCM
    all_points['TBCMVeloc'] = TBCMVeloc

    return undersampled_final_points, undersampled_COMs, undersampled_axes, undersampled_vectors, all_points, final_points, {"TBCM": TBCM} , {"TBCMVeloc": TBCMVeloc}, files_2D

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


def draw_anat_ax(plot, axes, COMs, frame, a_filter=[]):
    '''Draws the lines for each anat ax starting from its corresponding COM'''
    #TODO see if this can be done in one draw_line call (not sure if an array of colors is possible)
    froms = []
    tos = []
    for name in COMs:
        try:
            if name not in a_filter:
                froms.append(COMs[name])
                tos.append(axes[name]['X'])
        except Exception as error:
            print("draw x anat error", type(error).__name__)
    draw_line(plot, froms, tos, frame, 'red', name='AnatAx X')

    tos = []
    for name in COMs:   
        try:
            if name not in a_filter:
                tos.append(axes[name]['Y'])
        except Exception as error:
            print("draw y anat error", type(error).__name__)
    draw_line(plot, froms, tos, frame, 'green', name='AnatAx Y')

    tos = []
    for name in COMs:
        try:
            if name not in a_filter:
                tos.append(axes[name]['Z'])
        except Exception as error:
            print("draw z anat error", type(error).__name__)
    draw_line(plot, froms, tos, frame, 'blue', name='AnatAx Z')


    return plot

def draw_vectors(plot, vectors,  startingFrame, v_filter=[]):
    '''Draw the vectors
    Currently just a line from vector[key][0] to vector[key][1] at every frame'''
    froms = []
    tos = []
    for vector in vectors:
        if vector not in v_filter:
            froms.append(vectors[vector][0])
            tos.append(vectors[vector][1])
    plot = draw_line(plot, froms, tos, startingFrame, 'purple', name='Vectors')
    return plot

def base_plot(dfs, labels, frame):
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
    p_size = 1
    scene_scaling = dict(xaxis = dict(range=[x_min, x_max], autorange=False),
                        yaxis = dict(range=[y_min, y_max], autorange=False),
                        zaxis = dict(range=[z_min, z_max], autorange=False),
                        aspectmode='cube')
    #the figure (full library)
    main_plot = go.Figure(
        data=[go.Scatter3d( x=dfs[frame]['X'],
                            y=dfs[frame]['Y'], 
                            z=dfs[frame]['Z'],
                            mode='markers', #gets rid of line connecting all points
                            marker={'color':dfs[frame]['Segment_ID'], 'size': p_size},
                            hovertext= labels
                            ),
        ],
        layout=go.Layout(#TODO Setting that size of the plot seems to make it not responsive to a change in window size.
                        scene = scene_scaling,
                        title="BiomechOS",
                        margin=dict(l=0, r=0, b=0, t=0, pad=4),
                        updatemenus=[dict(type="buttons",
                                            x=0.9,
                                            y=0.5,
                                            direction="down",
                                            buttons=[dict(label="Play",
                                                        method="animate",
                                                        args=[None, {"fromcurrent": True, "frame": {"duration": 50, 'redraw': True}, "transition": {"duration": 0}}]), #TODO verify this controls the speed https://plotly.com/javascript/animations/
                                                    dict(label='Pause',
                                                        method="animate",
                                                        args=[[None], {"mode": "immediate"}]),
                                                    dict(label="Restart",
                                                        method="animate",
                                                        args=[None, {"frame": {"duration": 50, 'redraw': True}, "mode": 'immediate',}]),
                                                    ])],
                        legend=dict(
                            x=0.5,
                            y=1,
                            orientation='h',
                            xanchor='center',  # Center the legend horizontally
                            yanchor='bottom',
                        )
        ),
        frames=[go.Frame(
                data= [go.Scatter3d(
                            x=dfs[i]['X'],
                            y=dfs[i]['Y'], 
                            z=dfs[i]['Z'], 
                            mode='markers', #gets rid of line connecting all points
                            marker={'color':dfs[i]['Segment_ID'],  'size': p_size},
                            connectgaps=False, #TODO ask what we should do in this case.  Currently this stops the filling in of blanks/NaNs
                            hovertext = labels
                            ),
                            ])
                for i in range(frame, len(dfs))] #https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html
    )

    return main_plot

def draw_line(plot, froms, tos, startingFrame, cs='red', name='lines'):
    '''Add a line in all frames of plot from froms[x] to tos[x]'''

    #point list is [from, to, None] in a loop
    frames = []
    for n in range(startingFrame, len(froms[0])): #for every frame
        try:
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
        except Exception as error:
            print("line drawing error", type(error).__name__)

    try:
        plot.add_trace(go.Scatter3d(
            x=frames[0][0],
            y=frames[0][1],
            z=frames[0][2],
            mode='lines', line=dict(color=cs), name=name
        ))
    except Exception as error:
        print("continued line error", type(error).__name__)

    #one pass per frame for all lines O(n) where n = #frames
    for i, frame in enumerate(plot.frames):
        try:
            temp = list(frame.data)
            temp.append(go.Scatter3d(x=frames[i][0], y=frames[i][1], z=frames[i][2], mode='lines', line=dict(color=cs)))
            frame.data = temp
        except Exception as error:
            print("index error", type(error).__name__)

    return plot

def detect_filetype(filename):
    loaded = sio.loadmat(filename)
    if (loaded):
        loaded = loaded["Data"]
        if (np.shape(loaded) == (1,1)):
            loaded = load_from_mat(filename, {})
            key = list(loaded.keys())[0]
            loaded = loaded[key]
    shape = np.shape(loaded)
    filetype = ""
    if (len(shape) == 3 and shape[0] == 3 and shape[1] == 3):
        filetype = "axes"
    elif (len(shape) == 2 and shape[1] == 2):
        filetype = "linesegment"
    elif (len(shape) == 2 and shape[1] == 3):
        filetype = "point"
    else: #Need clarification on vector type to create accurate conditions
        filetype = "vector"

    return filetype

def UploadAction(event=None):
    filenames = filedialog.askopenfilenames()

    global filesList
    filesList = {'AnatAx' : [], 'SegCOM': [], 
             'TBCM' : [], 'TBCMVeloc' : [],
             'MocapData' : []}
            #https://stackoverflow.com/questions/1124810/how-can-i-find-path-to-given-file
    for filename in filenames:
        if "tbcm_" in filename.casefold():
            filesList['TBCM'].append(filename)
        if "tbcmveloc" in filename.casefold():
            filesList['TBCMVeloc'].append(filename)
        if "segcom" in filename.casefold():
            filesList['SegCOM'].append(filename)
        if "anatax" in filename.casefold():
            filesList['AnatAx'].append(filename)
        if "mocap" in filename.casefold():
            filesList['MocapData'].append(filename)

    global points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, selected_y_axis_point_2D, file_list_2D
    global dfs, labels
    global frameLength
    points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, file_list_2D = read_Mitchell_data(frameRate)
    selected_y_axis_point_2D = mocap_data_2D_graphs
    dfs, labels = filter_points_to_draw(points, COMs)
    frameLength = len(dfs) * frameRate
    root.destroy()
    dash()

def dash():
    app = Dash("plots", suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP]) #Suppress is true to allow divs to spawn divs without breaking system
    global frameLength
    global points

    app.layout = html.Div([ # Start of Dash App
        html.Link(
        rel='stylesheet',
        href='/assets/styles.css'  # Adjust the path to your CSS file
    ),
        html.Header(
        html.H1("BiomechOS", style={'textAlign': 'center'}),
        style={
            'background-color': '#4da2f7',  # Set the background color of the header
            'padding': '0px',
            'padding-top': '5px',  # Set padding for the header
            'padding-bottom': '5px',  # Set padding for the header
            'color': 'white',  # Set text color
            'width': '100%',

        }
    ),
    dbc.Modal(id = "newGraphModal", children=[
            dbc.ModalHeader("Add New 2D Graph", id='new-graph-modal-header'),
            dbc.ModalBody(id='new-graph-modal-body', children=[
                html.Div(id='new-graph-attributes-div', children=[
                    html.H5("Graph Attributes:"),
                    html.Div(id='new-graph-attributes-inputs-div', children=[
                        html.H6("Title:"), 
                        dcc.Input(id='new-graph-title-input', type='text', placeholder='My New 2D Graph'),
                        html.H6("X-Axis Title:"), 
                        dcc.Input(id='new-graph-x-axis-input', type='text', placeholder='X'),
                        html.H6("Y-Axis Title:"), 
                        dcc.Input(id='new-graph-y-axis-input', type='text', placeholder='Y'),
                        html.H6("Height:"), 
                        dcc.Input(id="new-graph-height-input", type="number", placeholder=300, value=300, min=200, max=1000, debounce=True, style={"height": "20px", "margin-left": "5px"})
                    ]),
                ]),
                html.H5("Select the data for the Y-Axis:"),

                html.H6("Select the File:"),
                dcc.Dropdown(
                    id='y-axis-select-file',
                    options=file_list_2D,
                    value='Mocap',
                    clearable=False,
                    style={'margin-bottom': '5px'}
                ),
                html.Div(id='new-graph-add-line-dropdowns-div', children = [ # Div that hold dropdown
                    html.Div(id='new-graph-line-1-title', children=[
                        html.H6("Line:", id='new-graph-modal-line-1-text'),
                    ]),
                    html.Div(id='new-graph-line-1-inputs',className='new-graph-line-inputs', children=[ 
                        dcc.Dropdown(
                            id={'type': 'new-graph-point-dropdown', 'index': f'{newGraphNumOfLines}'},
                            options=[{"label": point, "value": point} for point in selected_y_axis_point_2D.keys()],
                            value= list(selected_y_axis_point_2D.keys())[0],
                            clearable=False,
                            style={'width': '100%', 'margin-right': '4px'}
                        ),
                        dcc.Dropdown(
                            id={'type': 'new-graph-xyz-dropdown', 'index': f'{newGraphNumOfLines}'},
                            options=[{"label": "X", "value": "X"},
                                    {"label": "Y", "value": "Y"},
                                    {"label": "Z", "value": "Z"}],
                            value="X",
                            clearable=False,
                            style={'width': '10%', 'margin-right': '4px'}
                        ),     
                        dbc.Input(type="color", id={'type': 'new-graph-color-picker', 'index': f'{newGraphNumOfLines}'},value="#000000",style={"width": '10%', 'height': '36px'}),
                        dbc.Button("Remove", id='new-graph-original-remove-button', className='new-graph-remove-line-button')
                    ]),
                    ]),
                html.Div(id='new-graph-add-another-line-button-div', children=[dbc.Button("Add Another Line", id='new-graph-add-another-line-button')]),
                html.H5("Select the data for the X-Axis:", id="new-graph-x-axis-title"),
                html.P("(Default will be frames)"),
                html.H6("Select the File:"),
                dcc.Dropdown(
                    id='x-axis-select-file',
                    options=file_list_2D,
                    value='Mocap',
                    clearable=False,
                    style={'margin-bottom': '5px'}
                ),
                html.H6("Select the Data:"),
                html.Div(id="new-graph-x-axis-dropdown-div", children= [
                        dcc.Dropdown(
                            id="x-axis-point-dropdown",
                            options=[{"label": "Frames", "value": "frames"}] + [{"label": point, "value": point} for point in mocap_data_2D_graphs.keys()],
                            value= "frames",
                            clearable=False,
                            style={'width': '100%', 'margin-right': '4px'}
                        ),
                        dcc.Dropdown(
                            id="x-axis-xyz-dropdown",
                            options=[{"label": "X", "value": "X"},
                                    {"label": "Y", "value": "Y"},
                                    {"label": "Z", "value": "Z"}],
                            value="X",
                            clearable=False,
                            style={'width': '10%', 'margin-right': '4px', 'display': 'none'}
                        ),                             
                ]),
            ]),
            dbc.ModalFooter(id='new-graph-modal-footer', children=[dbc.Button("Cancel", id="cancel-add-new-modal", className="ml-auto", style={'background': '#ededed', 'color': 'black', 'border-color': 'black'}),
                             dbc.Button("Submit", id="submit-add-new-modal", className="ml-auto", style={'border-color': 'black'})]),
            ], backdrop="static",
    ), # End of the New Graph Modal
    html.Div([ # Start of the Div that holds EVERYTHING
        dcc.Location(
            id="url",
            pathname="/",
            refresh=True
        ),
        
        html.Div([ # Div to hold the dropdown stuff and the time series graphs
            html.Div([ #Div for the drop Down stuff
                html.Div([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Files')
                        ]),
                        style={
                            'width': '98%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        # Allow multiple files to be uploaded
                        multiple=True
                        ),
                html.H4('Interactive Graph Selection for Time Series', style={"margin": '0px', 'margin-top': '5px', 'margin-bottom': '5px'}),
                ]),
                html.Div(id='hidden-div', children=[
                    html.P('', id="chainCallback")
                ], style={'display':'none'}),
               
            ]),
            html.Div(id="outer-2d-graph-div", children=[ # Time Series Graphs Div
                html.Div(id="inner-2d-graph-div", children=[
                    html.Div(id='add-new-btn-and-graphs-div', children=[
                        html.Div(id="normal-graphs-div", children=[]),
                        html.Button("Add New 2D Graph", id="addNew2dGraphBtn")
                    ]),
                ]),
            ],
            style={ # Styling for the time Series Graphs Div
                'display': 'flex',
                'flex-direction': 'column',
                'overflow': 'auto',
                'max-height': '100vh'
            })
        ],
        style={ # Styling for the Div that holds the Dropdown menu and the Times Series Graph
            'display': 'flex',
            'flex-direction': 'column',
            'width': '50%',
            'margin-right': '10px'

        }),
        html.Div([  # Div for the Actual 3D Visualization
            html.Div([
                dcc.Checklist(
                    [
                        {
                            "label": html.Div(['Points'], style={'font-size': 20}),
                            "value": "Points", "disabled": True
                        },
                        {
                            "label": html.Div(['Line'], style={'font-size': 20}),
                            "value": "Line",
                        },
                        {
                            "label": html.Div(['Anatomical Axes'], style={'font-size': 20}),
                            "value": "Anatomical Axes",
                        },
                        {
                            "label": html.Div(['Vector'], style={'font-size': 20}),
                            "value": "Vector",
                        },
                    ], value=['Points'],
                    inline=True,
                    labelStyle={"display": "inline-block", "align-items": "center", "width" : "20%"},
                    id='3dGenChecklist'
                ),
                html.Button('Generate 3D Graph', id='3dGenButton', n_clicks=0)
            ])
            # End of div that holds all framrate, current frame inputs and the sliders
        ], 
        style={ # Styling for the 3D Visiaulization Div
            'display':'flex',
            'justify-content': 'center',
            'width': '50%',
            "height": "100vh",
            'flex-direction': 'column',
            'margin-left': '10px'
        }, id="3dGraphDiv"),        
    ],
    style={ #Styling for the Div that hold the two main divs (Dropdown and Times Series Divs, and the 3D Visualization Div)
        'display': 'flex',
        'width' : '100%',
        'flex-direction': 'row-reverse',
        'height': '90vh'
    }) # End of the Div that holds eveyrthing
    ],
    style={
        'width': '100%',
        'padding': '0px',
        'margin': '0px'
    }) # End of Dash App

   
    # Callback for drawing the 3D Plot
    @app.callback(
        Output("graph4", "figure"), 
        Input("3dGenButton", 'n_clicks'),
        Input("3dInputSlider", "value"),
        Input("3dFramerateInput", "value"),
        Input('upload-data', 'contents'),
        State('3dGenChecklist', 'value'))
    def draw_3d_graph(n_clicks, startingFrame, framerate, filecontents, checklistValues):
        global points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, file_list_2D
        global dfs, labels
        points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, file_list_2D = read_Mitchell_data(framerate)
        dfs, labels = filter_points_to_draw(points, COMs)
        main_plot = base_plot(dfs, labels, startingFrame // framerate)
        if 'Line' in checklistValues:
            main_plot = draw_line(main_plot, [COMs[list(COMs.keys())[0]], points[list(points.keys())[0]]], [COMs[list(COMs.keys())[1]], points[list(points.keys())[1]]], startingFrame // framerate)
        if 'Anatomical Axes' in checklistValues:
            main_plot = draw_anat_ax(main_plot, axes, COMs, startingFrame // framerate)
        if 'Vector' in checklistValues:
            main_plot = draw_vectors(main_plot, vectors, startingFrame // framerate)
        return main_plot

    @app.callback(
    Output("newGraphModal", "is_open"),
    Output('new-graph-add-line-dropdowns-div', 'children'),
    Output('x-axis-point-dropdown', 'value', allow_duplicate=True),
    Output('x-axis-xyz-dropdown', 'value', allow_duplicate=True),
    [Input("addNew2dGraphBtn", "n_clicks"),
    Input("cancel-add-new-modal", "n_clicks"),
    Input("submit-add-new-modal", "n_clicks")],
    [State("newGraphModal", "is_open"), State('new-graph-add-line-dropdowns-div', "children")], prevent_initial_call=True
    )   
    def toggle_add_new_modal(n_clicks_open, n_clicks_close, n_clicks_submit, is_open, current_children):
        global newGraphNumOfLines
        if n_clicks_open or n_clicks_close or n_clicks_submit:
            if newGraphNumOfLines != 1:
                newGraphNumOfLines = 1
                new_children = [html.Div([
                html.Div(id='new-graph-line-1-title', children=[
                html.H6("Line:", id='new-graph-modal-line-1-text'),
                ]),
                html.Div(id='new-graph-line-1-inputs',className='new-graph-line-inputs', children=[ 
                    dcc.Dropdown(
                        id={'type': "new-graph-point-dropdown", 'index': f'{newGraphNumOfLines}'},
                        options=[{"label": point, "value": point} for point in selected_y_axis_point_2D.keys()],
                        value= list(selected_y_axis_point_2D.keys())[0],
                        clearable=False,
                        style={'width': '100%', 'margin-right': '4px'}
                    ),
                    dcc.Dropdown(
                        id={'type': 'new-graph-xyz-dropdown', 'index': f'{newGraphNumOfLines}'},
                        options=[{"label": "X", "value": "X"},
                                {"label": "Y", "value": "Y"},
                                {"label": "Z", "value": "Z"}],
                        value="X",
                        clearable=False,
                        style={'width': '10%', 'margin-right': '4px'}
                    ), dbc.Input(type="color", id={'type': 'new-graph-color-picker', 'index': f'{newGraphNumOfLines}'},value="#000000",style={"width": '10%', 'height': '36px'}),
                    dbc.Button("Remove", id='new-graph-original-remove-button', className='new-graph-remove-line-button')])])]
                
                return not is_open, new_children, 'frames', 'X'
            else:
                return not is_open, current_children, 'frames', 'X'        
        else:
            return is_open, current_children, 'frames', 'X'
        
    @app.callback(
        Output('new-graph-add-line-dropdowns-div', 'children', allow_duplicate=True),
        Input('new-graph-add-another-line-button', 'n_clicks'),
        State('new-graph-add-line-dropdowns-div', "children"),
        prevent_initial_call=True
    )
    def add_line_options(n_clicks, current_children):
        global points
        global newGraphNumOfLines

        newGraphNumOfLines = newGraphNumOfLines + 1

        current_children.append(html.Div(id={'type': 'new-graph-dynamically-added-inputs-div', 'index': f'{newGraphNumOfLines}'}, children=[
            html.Div(id=f'new-graph-line-{newGraphNumOfLines}-title', children=[
                        html.H6(f"Line:", id=f'new-graph-modal-line-{newGraphNumOfLines}-text'),
                    ]),
                    html.Div(id={'type': 'new-graph-dynamic-inputs-div', 'index': f'{newGraphNumOfLines}'},className='new-graph-line-inputs', children=[ 
                        dcc.Dropdown(
                            id={'type': 'new-graph-point-dropdown', 'index': f'{newGraphNumOfLines}'},
                            options=[{"label": point, "value": point} for point in selected_y_axis_point_2D.keys()],
                            value= list(selected_y_axis_point_2D.keys())[0],
                            clearable=False,
                            style={'width': '100%', 'margin-right': '4px'}
                        ),
                        dcc.Dropdown(
                            id={'type': 'new-graph-xyz-dropdown', 'index': f'{newGraphNumOfLines}'},
                            options=[{"label": "X", "value": "X"},
                                    {"label": "Y", "value": "Y"},
                                    {"label": "Z", "value": "Z"}],
                            value="X",
                            clearable=False,
                            style={'width': '10%', 'margin-right': '4px'}
                        ),     
                        dbc.Input(type="color", id={'type': 'new-graph-color-picker', 'index': f'{newGraphNumOfLines}'},value="#000000",style={"width": '10%', 'height': '36px'}),
                        dbc.Button("Remove", id={'type': 'new-graph-remove-line', 'index':f'{newGraphNumOfLines}'}, className='new-graph-remove-line-button'),
                    ])]))


        return current_children
        
    @app.callback(
        [Output("normal-graphs-div", "children", allow_duplicate=True),
            Output('new-graph-title-input', 'value'),
            Output('new-graph-x-axis-input', 'value'),
            Output('new-graph-y-axis-input', 'value'),
            Output('new-graph-height-input', 'value'),
            Output('x-axis-point-dropdown', 'value'),
            Output('x-axis-xyz-dropdown', 'value'),],
        [Input("submit-add-new-modal", "n_clicks")],
        [State({"type": "new-graph-point-dropdown", "index": ALL}, "value"),
        State({"type": "new-graph-xyz-dropdown", "index": ALL}, "value"),
        State({"type": "new-graph-color-picker", "index": ALL}, "value"),
        State('x-axis-point-dropdown', 'value'),
        State('x-axis-xyz-dropdown', 'value'),
        State('new-graph-title-input', 'value'),
        State('new-graph-x-axis-input', 'value'),
        State('new-graph-y-axis-input', 'value'),
        State('new-graph-height-input', 'value'),
        State("normal-graphs-div", "children")], prevent_initial_call=True
    )
    def add_new_graph(submit_clicks, selected_point_keys, selected_xyzs, lineColors, x_axis_point, x_axis_xyz, title, x_axis_title, y_axis_title, height, current_children):
        global numOf2dGraphs
        global all_points_for_2D_graphs
        fig = go.Figure()
        y_title_not_given = False

        if y_axis_title is None: 
            y_title_not_given = True
            y_axis_title = ""
        if height is None: height = 300

        for i in range(len(selected_point_keys)):
            selected_point_key = selected_point_keys[i]
            selected_xyz = selected_xyzs[i]
            lineColor = lineColors[i]
            if y_title_not_given:
                y_axis_title = y_axis_title + selected_point_key + "_" + selected_xyz
                if i < len(selected_point_keys)-1:
                    y_axis_title += ", "

            selected_point = all_points_for_2D_graphs[selected_point_key]  


            if selected_xyz == "X":
                point = selected_point[:, 0].T
            elif selected_xyz == "Y":
                point = selected_point[:, 1].T
            elif selected_xyz == "Z":
                point = selected_point[:, 2].T

            if(i==0):
                if(x_axis_point == "frames"):
                    if x_axis_title is None: x_axis_title = "Frames"
                    x_axis_point = list(range(len(point)))
                else:
                    if x_axis_title is None: x_axis_title = x_axis_point + "_" + x_axis_xyz

                    x_axis_point = all_points_for_2D_graphs[x_axis_point]
                    if x_axis_xyz == "X":
                        x_axis_point = x_axis_point[:, 0].T
                    elif x_axis_xyz == "Y":
                        x_axis_point = x_axis_point[:, 1].T
                    elif x_axis_xyz == "Z":
                        x_axis_point = x_axis_point[:, 2].T

            fig.add_trace(go.Scatter(x=x_axis_point , y=point, mode='markers+lines', line=dict(color=lineColor), name=f"{selected_point_key} {selected_xyz}"))
        
        if title is None: title = y_axis_title + " Plotted Over " + x_axis_title

        fig.update_layout(title=title, xaxis_title=x_axis_title,
                                            yaxis_title=y_axis_title, height=height)
        

        if submit_clicks:
            numOf2dGraphs = numOf2dGraphs + 1 
            current_children.append(html.Div(className='dynamically-added-graph-divs', id={'type':'dynamically-added-graph-divs', 'index':f'{numOf2dGraphs}'}, children=[
                                        dcc.Graph(figure=fig),
                                        html.Div(className='dynaimically-add-button-div', id={'type': 'button-div', 'index':f'{numOf2dGraphs}'}, children=[
                                            html.Button("Remove Graph",className='remove-graph-button', id={'type':'remove-button', 'index': f'{numOf2dGraphs}'}, style={'margin': '10px'})
                                        ]),
                                        ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'flex-direction': 'column'})) 

        return current_children, None, None, None, 300, "frames", " "
    
    @app.callback(
    Output({'type': "new-graph-point-dropdown", 'index': MATCH}, "options", allow_duplicate=True),
    Output({'type': "new-graph-point-dropdown", 'index': MATCH}, "value", allow_duplicate=True),
    [Input("y-axis-select-file", "value")], prevent_initial_call='initial_duplicate'
    )
    def update_y_axis_options(selected_value):
        if selected_value == "Mocap":
            return [{"label": point, "value": point} for point in mocap_data_2D_graphs.keys()], list(mocap_data_2D_graphs.keys())[0]
        elif selected_value == "TBCM":
            return [{"label": point, "value": point} for point in TBCM_2D_graphs.keys()],  list(TBCM_2D_graphs.keys())[0]
        elif selected_value == "TBCMVeloc":
            return [{"label": point, "value": point} for point in TBCMVeloc_2D_graphs.keys()],  list(TBCMVeloc_2D_graphs.keys())[0]

    @app.callback(
    Output("x-axis-point-dropdown", "options"),
    [Input("x-axis-select-file", "value")], prevent_initial_call=True
    )
    def update_x_axis_options(selected_value):
        if selected_value == "Mocap":
            return [{"label": "Frames", "value": "frames"}] + [{"label": point, "value": point} for point in mocap_data_2D_graphs.keys()]
        elif selected_value == "TBCM":
            return [{"label": "Frames", "value": "frames"}] + [{"label": point, "value": point} for point in TBCM_2D_graphs.keys()]
        elif selected_value == "TBCMVeloc":
            return [{"label": "Frames", "value": "frames"}] + [{"label": point, "value": point} for point in TBCMVeloc_2D_graphs.keys()]


    @app.callback(
    Output("x-axis-xyz-dropdown", "style"),
    Input("x-axis-point-dropdown", "value")
    )
    def update_xyz_dropdown_style(selected_point):
        if selected_point == "frames":
            return {'display': 'none'}
        else:
            return {'display': 'block'}
    
    @app.callback(
        Output({'type':'dynamically-added-graph-divs', 'index': MATCH}, 'children'),
        [Input({'type': 'remove-button', 'index': MATCH}, 'n_clicks')],
        [State({'type':'dynamically-added-graph-divs', 'index': MATCH}, 'children'),
        State('normal-graphs-div', 'children')],
        prevent_initial_call=True
    )
    def remove_element(n_clicks, child, current_children):

        if n_clicks is not None:
            updated_children = [div for div in current_children if child[1]['props']['id'] == div['props']['id']]
       
            return updated_children

        return current_children

    @app.callback(
            Output({'type': 'new-graph-dynamically-added-inputs-div', 'index': MATCH}, 'children'),
            Input({'type': 'new-graph-remove-line', 'index':MATCH}, 'n_clicks'),
            State({'type': 'new-graph-dynamically-added-inputs-div', 'index': MATCH}, 'children'),
            prevent_initial_call=True
    )
    def remove_new_lines_add_new_graph(n_clicks, current_children):
        return []
  
    @app.callback(
        Output("3dInput", "value"),
        Output("3dInputSlider", "value"),
        Input("3dInput", "value"),
        Input("3dInputSlider", "value"),)
    def callback(start, slider):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        start_value = start if trigger_id == "3dInput" else slider
        slider_value = slider if trigger_id == "3dInputSlider" else start_value

        return start_value, slider_value
    
    @app.callback(
        Output("sliderDiv", "children"),
        Input("3dFramerateInput", "value"),
        Input('chainCallback', 'children'))
    def callback(framerate, chainCallbackValue):
        global frameLength

        div = html.Div([
            dcc.Slider(
                0, frameLength, 1,
                value=0,
                id='3dInputSlider'
            )
        ], id="sliderDiv")

        return div
    
    @app.callback(
        Output("3dGraphDiv", "children"),
        Input("3dGenButton", "n_clicks"),
        State("3dGraphDiv", "children"),
        prevent_inital_call=True,
        running=[(Output("3dGenButton", "disabled"), True, False)]
        )
    def callback(n_clicks, ogChildren):

        print(n_clicks)
        if n_clicks == 0 or n_clicks is None:
            return no_update
        else:

            div1 = html.Div([ # Div of the 3D graph Only
                        dcc.Loading(
                            id="loading-graph4",
                            type="default",
                            children=[
                                dcc.Input(id='dummy-input', value='dummy-value', style={'display': 'none'}),
                                dcc.Graph(id="graph4", config={'responsive': True}),
                            ]
                        ),
                    ], style={"height": "50vh"}) # End of Div for the 3D graph only
            div2 =  html.Div([ # Start of div that holds all framrate, current frame inputs and the sliders
                        html.Div([ # Start of div that holds both the framerate and current frame inputs
                            html.Div([ # Start of div that holds the framerate input
                                html.P("Framerate Input:", style={ "font-weight": "bold", 'margin': '0px'}),
                                dcc.Input(
                                    id="3dFramerateInput", type="number", placeholder="", value=8, debounce=True, style={"height": "20px", "margin-left": "5px"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "flex-direction": "row",
                                "align-items": "center",
                                "justify-content": "center",
                                "flex-wrap": 'wrap'
                            }), # End of div that holds the framerate input
                            html.Div([ # Start of div that holds the Current frame input
                                html.P('Current Frame:', style={ "font-weight": "bold", 'margin': '0px'}),
                                dcc.Input(
                                    id="3dInput", type="number", placeholder="", value=1000, debounce=True, style={"height": "20px", "margin-left": "5px"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "flex-direction": "row",
                                "align-items": "center",
                                "justify-content": "center",
                                "flex-wrap": 'wrap'
                            }), # End of div that holds the Current frame input
                        ],
                        style={
                            "display": "flex",
                            "flex-direction": "row",
                            "align-items": "center",
                            "justify-content": "space-around",
                            "flex-wrap": 'wrap',
                            'margin-top': '30px',
                            'margin-bottom': '30px'

                        })]) # End of div that holds both the framerate and current frame inputs
            div3 = html.P('Frame Slider', style={"margin": "0px", "font-weight": "bold"})
            div4 = html.Div([
                        dcc.Slider(
                            0, frameLength, 1,
                            value=0,
                            id='3dInputSlider',
                        )], id="sliderDiv")

            div6 = html.Div([div1, div2, div3, div4])
            newChildren = [ogChildren[0], div6]

            return newChildren
    
    @app.callback(
        Output({"type": "new-graph-point-dropdown", "index": '1'}, "value"),
        Output({"type": "new-graph-point-dropdown", "index": '1'}, "options"),
        Output('chainCallback', 'children'),
        Output("normal-graphs-div", 'children'),
        Output('y-axis-select-file', 'options'),
        Output('x-axis-select-file', 'options'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('upload-data', 'last_modified'),
        prevent_initial_call=True)
    def update_output(list_of_contents, list_of_names, list_of_dates):
        if list_of_contents is not None:
            global filesList, removedTraces
            filesList = {'AnatAx' : [], 'SegCOM': [], 
             'TBCM' : [], 'TBCMVeloc' : [],
             'MocapData' : []}
            TBCMnew = False
            TBCMVelocNew = False
            AnatAxNew = False
            SegComNew = False
            MocapNew = False
            #https://stackoverflow.com/questions/1124810/how-can-i-find-path-to-given-file
            for filename in list_of_names:
                for root, dirs, files in os.walk(os.getcwd()):
                    for name in files:
                        if name == filename:
                            if "tbcm_" in filename.casefold():
                                if not TBCMnew:
                                    filesList['TBCM'] = []
                                filesList['TBCM'].append(os.path.abspath(os.path.join(root, name)))
                                TBCMnew = True
                            if "tbcmveloc" in filename.casefold():
                                if not TBCMVelocNew:
                                    filesList['TBCMVeloc'] = []
                                filesList['TBCMVeloc'].append(os.path.abspath(os.path.join(root, name)))
                                TBCMVelocNew = True
                            if "segcom" in filename.casefold():
                                if not SegComNew:
                                    filesList['SegCOM'] = []
                                filesList['SegCOM'].append(os.path.abspath(os.path.join(root, name)))
                                SegComNew = True
                            if "anatax" in filename.casefold():
                                if not AnatAxNew:
                                    filesList['AnatAx'] = []
                                filesList['AnatAx'].append(os.path.abspath(os.path.join(root, name)))
                                AnatAxNew = True
                            if "mocap" in filename.casefold():
                                if not MocapNew:
                                    filesList['MocapData'] = []
                                filesList['MocapData'].append(os.path.abspath(os.path.join(root, name)))
                                MocapNew = True
            global points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, selected_y_axis_point_2D, file_list_2D
            global dfs, labels
            global frameLength
            global numOf2dGraphs
            numOf2dGraphs=0
            points, COMs, axes, vectors, all_points_for_2D_graphs, mocap_data_2D_graphs, TBCM_2D_graphs, TBCMVeloc_2D_graphs, file_list_2D = read_Mitchell_data(frameRate)
            selected_y_axis_point_2D = mocap_data_2D_graphs
            dfs, labels = filter_points_to_draw(points, COMs)
            frameLength = len(dfs) * frameRate
            return list(points.keys())[0], list(points.keys()), frameLength, [], file_list_2D, file_list_2D 

    #When giving code, set debug to False to make only one tkinter run needed
    app.run_server(debug=False)

figureX = ""
figureY = ""
figureZ = ""
frameRate = 8

global points, COMs, axes, vectors
global dfs, labels

root = tk.Tk()
root.geometry("300x100")
root.config(bg = "#d6d6d6")
root.title("BiomechOS")
root.resizable(False,False)
text = tk.Label(root, text = "Select Files to Use:", font=("Times New Roman", "12"), padx=5, pady=5, bg="#d6d6d6")
text.pack(side="left")
button = tk.Button(root, text='Browse', relief=tk.RAISED, bd=2, command=UploadAction)
button.pack(side="left")

root.mainloop()
