import plotly.express as px
import plotly.graph_objects as go
import scipy.io as sio
import numpy as np
import pandas as pd
import sys
from dash import Dash, dcc, html, Input, Output, State, callback_context, MATCH, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import os
import tkinter as tk
from tkinter import filedialog

#TODO color groups more distinctly 
#want the df to hold group names instead of a numerical id for the group names
#TODO the animation to be faster or at least adjustable
#TODO want a bar for the frame number
#TODO plot axis
# note we can use the add trace thing to make it so you can click to show points/groups and lines
global removesTraces
removedTraces=[]
global numOf2dGraphs
numOf2dGraphs= 0
global filesList
filesList = {}
filesList = {'AnatAx' : f'', 'SegCOM': f'', 
             'TBCM' : f'', 'TBCMVeloc' : f'',
             'MocapData' : f''}

def load_from_mat(filename=None, data={}, loaded=None):
    '''Turn .mat file to nested dict of all values
    Pulled from https://stackoverflow.com/questions/62995712/extracting-mat-files-with-structs-into-python'''
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

def read_Mitchell_data(framerate):
    '''Read Mitchell data 
    Specified as a folder with hardcoded to contain exactly the five sample folders for now
    Folder path is sys.argv[1]
    Returns dictonary of COM dfs and dictonary of points dfs'''
    #TODO update to take general file names in given folder
    #Note: The data dict in load_from_math seems to carry over somehow? If I don't set it to {} Then SegCOM will change once we read MocapData for example - Gavin
    #folder_path = sys.argv[1]
    # AnatAx => key = seg name, val = 3x3xN array for location so [frame][x_axis,y_axis,z_axis][x,y,z]
    AnatAx = load_from_mat(filesList['AnatAx'], {})
    #TBCMVeloc => need to read seperately.  It just has a data array which is Nx3 for locations
    TBCMVeloc = sio.loadmat(filesList['TBCMVeloc'], struct_as_record=True)['Data']
    #TBCM => need to read seperately.  It just has a data array which is Nx3 for locations 
    TBCM  = sio.loadmat(filesList['TBCM'], struct_as_record=True)['Data']
    # SegCOM => key = seg name, val = Nx3 array for location (only first value populated?)
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
    
    vectors['TBCM'][0] = TBCM
    vectors['TBCM'][1] = TBCM + TBCMVeloc

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

    
    undersampled_final_points = {key: value[::framerate] for key, value in final_points.items()}
    # Undersample COMs
    undersampled_COMs = {key: value[::framerate] for key, value in COMs.items()}
    # Undersample vectors
    undersampled_vectors = {key: [value[0][::framerate], value[1][::framerate]] for key, value in vectors.items()}
    # Undersample axes
    undersampled_axes = {}
    for ax, temp in axes.items():
        undersampled_axes[ax] = {coord: data[::framerate] for coord, data in temp.items()}

    return undersampled_final_points, undersampled_COMs, undersampled_axes, undersampled_vectors

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
        if name not in a_filter:
            froms.append(COMs[name])
            tos.append(axes[name]['X'])
    draw_line(plot, froms, tos, frame, 'red', name='AnatAx X')

    tos = []
    for name in COMs:   
        if name not in a_filter:
            tos.append(axes[name]['Y'])
    draw_line(plot, froms, tos, frame, 'green', name='AnatAx Y')

    tos = []
    for name in COMs:
        if name not in a_filter:
            tos.append(axes[name]['Z'])
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

# def draw_timeseries(point, point_name=''):
#     '''Shows x, y and z timeseries for a given point'''
#     x = point[:,0].T
#     y = point[:,1].T
#     z = point[:,2].T
#     time = list(range(len(z)))

#     fig_x = go.Figure(data=go.Scatter(x=time, y=x, mode='markers+lines', line=dict(color='red')), layout=go.Layout(title=f'Point {point_name} X over time', xaxis_title='Frame', yaxis_title='X'))
#     fig_y = go.Figure(data=go.Scatter(x=time, y=y, mode='markers+lines', line=dict(color='green')), layout=go.Layout(title=f'Point {point_name} Y over time', xaxis_title='Frame', yaxis_title='Y'))
#     fig_z = go.Figure(data=go.Scatter(x=time, y=z, mode='markers+lines', line=dict(color='blue')), layout=go.Layout(title=f'Point {point_name} Z over time', xaxis_title='Frame', yaxis_title='Z'))

#     fig_x.update_layout(
#         height=300,
#     )
#     fig_y.update_layout(
#         height=300,  
#     )
#     fig_z.update_layout(
#         height=300,
#     )

#     fig_combined = go.Figure(data=[
#         go.Scatter(x=time, y=x, mode='markers+lines', name='X', line=dict(color='red')),
#         go.Scatter(x=time, y=y, mode='markers+lines', name='Y', line=dict(color='green')),
#         go.Scatter(x=time, y=z, mode='markers+lines', name='Z', line=dict(color='blue'))
#     ], layout=go.Layout(title=f'Combined Graph for {point_name}', xaxis_title='Frame', yaxis_title='Value'))

#     return [fig_x, fig_y, fig_z, fig_combined]

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
            #https://stackoverflow.com/questions/1124810/how-can-i-find-path-to-given-file
    for filename in filenames:
        if "tbcm_" in filename.casefold():
            filesList['TBCM'] = filename
        if "tbcmveloc" in filename.casefold():
            filesList['TBCMVeloc'] = filename
        if "segcom" in filename.casefold():
            filesList['SegCOM'] = filename
        if "anatax" in filename.casefold():
            filesList['AnatAx'] = filename
        if "mocap" in filename.casefold():
            filesList['MocapData'] = filename

    global points, COMs, axes, vectors
    global dfs, labels
    global frameLength
    points, COMs, axes, vectors = read_Mitchell_data(frameRate)
    dfs, labels = filter_points_to_draw(points, COMs)
    frameLength = len(dfs) * frameRate
    root.destroy()
    dash()

def dash():
    app = Dash("plots", external_stylesheets=[dbc.themes.BOOTSTRAP])
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
    
    dbc.Modal(id = "customizeGraphModal", children=[
            dbc.ModalHeader("2D Graph Customizer"),
            dbc.ModalBody("This is a basic modal. You can add any content here."),
            dbc.ModalFooter(dbc.Button("Close", id="close-customize-modal", className="ml-auto")),
            ], backdrop="static",
    ),
    dbc.Modal(id = "newGraphModal", children=[
            dbc.ModalHeader("Add New 2D Graph"),
            dbc.ModalBody([
                html.H5("Select the data you would like to graph:"),
                html.Div([ # Div that hold dropdown
                    dcc.Dropdown(
                        id="addNewGraphDropdown",
                        options=[{"label": point, "value": point} for point in points.keys()],
                        value= list(points.keys())[0],
                        clearable=False,
                        style={'width': '100%', 'margin-right': '4px'}
                    ),
                    dcc.Dropdown(
                        id="xyzDropdown",
                        options=[{"label": "X", "value": "X"},
                                {"label": "Y", "value": "Y"},
                                {"label": "Z", "value": "Z"}],
                        value="X",
                        clearable=False,
                        style={'width': '10%', 'margin-right': '4px'}
                    ),     
                    dbc.Input(type="color", id="colorpicker",value="#000000",style={"width": '10%', 'height': '36px'}),
                    ],style={
                    'display': 'flex',
                    'flex-direction': 'row',
                    'justify-content': 'space-between',
                }) 

            ]),
            dbc.ModalFooter([dbc.Button("Cancel", id="cancel-add-new-modal", className="ml-auto", style={'background': '#ededed', 'color': 'black', 'border-color': 'black'}),
                             dbc.Button("Submit", id="submit-add-new-modal", className="ml-auto", style={'border-color': 'black'})]),
            ], backdrop="static",
    ),
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
                html.H4('Interactive Graph Selection for Time Series', style={"margin": '0px', 'margin-top': '5px'}),
                ]),
                html.Div(id='hidden-div', children=[
                    html.P('', id="chainCallback")
                ], style={'display':'none'}),
                html.Div([ # Div that hold dropdown and check box
                    dcc.Checklist(['View Combined Graph'], id='checkbox_hide')
                ],
                style={
                    'display': 'flex',
                    'flex-direction': 'column'   
                }) # End of Div that holds dropdown an checkbox
                
            ]),
            html.Div(id="outer-2d-graph-div", children=[ # Time Series Graphs Div
                html.Div(id="inner-2d-graph-div", children=[
                    html.Div(id='add-new-btn-and-graphs-div', children=[
                        html.Div(id="normal-graphs-div", children=[]),
                        html.Button("Add New 2D Graph", id="addNew2dGraphBtn")
                    ]),
                    html.Div( id = "combined-graph-div", children=[
                        dcc.Graph(id='graph-combined'),
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
            html.Div([ # Div of the 3D graph Only
                dcc.Loading(
                    id="loading-graph4",
                    type="default",
                    children=[
                        dcc.Input(id='dummy-input', value='dummy-value', style={'display': 'none'}),
                        dcc.Graph(id="graph4", config={'responsive': True}),
                    ]
                ),
            ], style={"height": "50vh"}), # End of Div for the 3D graph only
            html.Div([ # Start of div that holds all framrate, current frame inputs and the sliders
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

                }), # End of div that holds both the framerate and current frame inputs
            html.P('Frame Slider', style={"margin": "0px", "font-weight": "bold"}),
            html.Div([
                dcc.Slider(
                    0, frameLength, 1,
                    value=0,
                    id='3dInputSlider',
                )], id="sliderDiv")
            ]), # End of div that holds all framrate, current frame inputs and the sliders
        ],
        style={ # Styling for the 3D Visiaulization Div
            'display':'flex',
            'justify-content': 'center',
            'width': '50%',
            "height": "100vh",
            'flex-direction': 'column',
            'margin-left': '10px'
        }),        
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
        Input("3dInputSlider", "value"),
        Input("3dFramerateInput", "value"),
        Input('upload-data', 'contents'))
    def draw_3d_graph(startingFrame, framerate, filecontents):
        global points, COMs, axes, vectors
        global dfs, labels
        points, COMs, axes, vectors = read_Mitchell_data(framerate)
        dfs, labels = filter_points_to_draw(points, COMs)
        main_plot = base_plot(dfs, labels, startingFrame // framerate)
        main_plot = draw_line(main_plot, [COMs[list(COMs.keys())[0]], points[list(points.keys())[0]]], [COMs[list(COMs.keys())[1]], points[list(points.keys())[1]]], startingFrame // framerate)
        main_plot = draw_anat_ax(main_plot, axes, COMs, startingFrame // framerate)
        main_plot = draw_vectors(main_plot, vectors, startingFrame // framerate)
        return main_plot


    # @app.callback(
    #     Output("inner-2d-graph-div", "children"),
    #     [Input("addNew2dGraphBtn", "n_clicks")],
    #     [State("inner-2d-graph-div", "children")], prevent_initial_call=True
    # )
    # def add_graph(n_clicks, current_children):

    @app.callback(
    Output("newGraphModal", "is_open"),
    [Input("addNew2dGraphBtn", "n_clicks"),
    Input("cancel-add-new-modal", "n_clicks"),
    Input("submit-add-new-modal", "n_clicks")],
    [State("newGraphModal", "is_open")]
    )   
    def toggle_add_new_modal(n_clicks_open, n_clicks_close, n_clicks_submit, is_open):
        if n_clicks_open or n_clicks_close or n_clicks_submit:
            return not is_open
        else:
            return is_open
        
    @app.callback(
        [Output("normal-graphs-div", "children", allow_duplicate=True),
            Output("graph-combined", "figure", allow_duplicate=True)],
        [Input("submit-add-new-modal", "n_clicks")],
        [State("addNewGraphDropdown", "value"),
        State("xyzDropdown", "value"), 
        State("normal-graphs-div", "children"),
        State("graph-combined", "figure"), 
        State("colorpicker", "value")], prevent_initial_call=True
    )
    def add_new_graph(submit_clicks, selected_point_key, selected_xyz, current_children, current_combined_figure, lineColor):
        global numOf2dGraphs
        current_combined_figure = go.Figure(current_combined_figure)

        selected_point = points[selected_point_key]  

        if selected_xyz == "X":
            point = selected_point[:, 0].T
            # lineColor = "red"
        elif selected_xyz == "Y":
            point = selected_point[:, 1].T
            # lineColor = "green"
        elif selected_xyz == "Z":
            point = selected_point[:, 2].T
            # lineColor = "blue"

        time = list(range(len(point)))

        if current_combined_figure is None:
            current_combined_figure = go.Figure()

        if submit_clicks:
            numOf2dGraphs = numOf2dGraphs + 1     

            fig = go.Figure(data=go.Scatter(x=time, y=point, mode='markers+lines', line=dict(color=lineColor)),
                            layout=go.Layout(title=f'Point {selected_point_key} {selected_xyz} over time', xaxis_title='Frame',
                                            yaxis_title=f'{selected_xyz}', height=300))
            current_children.append(html.Div(className='dynamically-added-graph-divs', id={'type':'dynamically-added-graph-divs', 'index':f'{numOf2dGraphs}'}, children=[
                                        dcc.Graph(figure=fig),
                                        html.Button("Remove Graph",className='remove-graph-button', id={'type':'remove-button', 'index': f'{numOf2dGraphs}'}, style={'margin': '10px'})
                                        ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'flex-direction': 'column'})) 
            current_combined_figure.add_trace(go.Scatter(x=time, y=point, mode='markers+lines', line=dict(color=lineColor), name=f"{selected_point_key} {selected_xyz}"))    
            current_combined_figure.update_layout(title=f'Combined Graph of all data points selected over time',
                                              xaxis_title='Frame', yaxis_title='Value', height=600)  
            return current_children, current_combined_figure
        
        return current_children, current_combined_figure

    @app.callback(
        Output({'type':'dynamically-added-graph-divs', 'index': MATCH}, 'children'),
        [Input({'type': 'remove-button', 'index': MATCH}, 'n_clicks')],
        [State({'type':'dynamically-added-graph-divs', 'index': MATCH}, 'children'),
        State('normal-graphs-div', 'children'),
        State("graph-combined", "figure")],
        prevent_initial_call=True
    )
    def remove_element(n_clicks, child, current_children, current_combined_figure):
        global removedTraces

        if n_clicks is not None:
            updated_children = [div for div in current_children if child[1]['props']['id'] == div['props']['id']]
            current_combined_figure = go.Figure(current_combined_figure)
            words = child[0]['props']['figure']['layout']['title']['text'].split(' ')

            removedTraces.append(f'{words[1]} {words[2]}')
        
            return updated_children

        return current_children

    # @app.callback(
    # Output("customizeGraphModal", "is_open"),
    # [Input("customize2dGraph-1", "n_clicks"),
    #  Input("close-customize-modal", "n_clicks")],
    # [State("customizeGraphModal", "is_open")]
    # )
    # def toggle_customize_modal(n_clicks_open, n_clicks_close, is_open):
    #     if n_clicks_open or n_clicks_close:
    #         return not is_open
    #     else:
    #         return is_open
    
    #Callback for showing Either three seperate graphs or showing one combined Graph
    @app.callback(
        [Output('add-new-btn-and-graphs-div', 'style'), Output('graph-combined', 'figure'),  Output('combined-graph-div', 'style')],
        [Input("checkbox_hide", "value")],
        State("graph-combined", "figure")
    )
    def update_graph_visibility(checkbox_value, current_combined_figure):
        global removedTraces
        if checkbox_value:
            current_combined_figure = go.Figure(current_combined_figure)
            new_fig = go.Figure(layout=go.Layout(title=f'Combined Graph of all data point selected over time', xaxis_title='Frame', yaxis_title='Value', height=600))
            if removedTraces != []:
                for line in current_combined_figure.data:
                    if line['name'] not in removedTraces :
                        new_fig.add_trace(line)

                removedTraces = []
                current_combined_figure = new_fig

            return {'display': 'none'}, current_combined_figure,{'display': 'block'}
        else:
            current_combined_figure = go.Figure(current_combined_figure)
            return {'display': 'block'}, current_combined_figure, {'display': 'none'}
    
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
        Output('addNewGraphDropdown', 'value'),
        Output('addNewGraphDropdown', 'options'),
        Output('chainCallback', 'children'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('upload-data', 'last_modified'),
        prevent_initial_call=True)
    def update_output(list_of_contents, list_of_names, list_of_dates):
        if list_of_contents is not None:
            global filesList
            #https://stackoverflow.com/questions/1124810/how-can-i-find-path-to-given-file
            for filename in list_of_names:
                for root, dirs, files in os.walk(os.getcwd()):
                    for name in files:
                        if name == filename:
                            if "tbcm_" in filename.casefold():
                                filesList['TBCM'] = os.path.abspath(os.path.join(root, name))
                            if "tbcmveloc" in filename.casefold():
                                filesList['TBCMVeloc'] = os.path.abspath(os.path.join(root, name))
                            if "segcom" in filename.casefold():
                                filesList['SegCOM'] = os.path.abspath(os.path.join(root, name))
                            if "anatax" in filename.casefold():
                                filesList['AnatAx'] = os.path.abspath(os.path.join(root, name))
                            if "mocap" in filename.casefold():
                                filesList['MocapData'] = os.path.abspath(os.path.join(root, name))
            # read_Mitchell_data(frameRate)
            global points, COMs, axes, vectors
            global dfs, labels
            global frameLength
            global numOf2dGraphs
            numOf2dGraphs=0
            points, COMs, axes, vectors = read_Mitchell_data(frameRate)
            dfs, labels = filter_points_to_draw(points, COMs)
            frameLength = len(dfs) * frameRate
            allLineGraphed ={}
            return list(points.keys())[0], list(points.keys()), frameLength


    #When giving code, set debug to False to make only one tkinter run needed
    app.run_server(debug=True)

figureX = ""
figureY = ""
figureZ = ""
frameRate = 8

global points, COMs, axes, vectors
global dfs, labels
global allLineGraphed


root = tk.Tk()
root.geometry("300x100")
root.config(bg = "#d6d6d6")
root.title("BiomechOS")
root.resizable(False,False)
text = tk.Label(root, text = "Selct Files to Use:", font=("Times New Roman", "12"), padx=5, pady=5, bg="#d6d6d6")
text.pack(side="left")
button = tk.Button(root, text='Browse', relief=tk.RAISED, bd=2, command=UploadAction)
button.pack(side="left")

root.mainloop()
