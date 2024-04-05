# BiomechOS

Within the research space, there are few tools that can be leveraged by labs for data visualization and analysis. This often leaves researchers to create their own tool to visualize their data. With BiomechOS we hope to solve the problem of standardization of data visualization tools for lab settings. BiomechOS will be capable of receiving a variety of import data, creating time series graphs in 2D space, generating 3D visualizations using a point and line system, and allowing user interaction with the visualized data. This will allow researchers to effectively view their data and deepen their analysis.

## Table of Contents

-   [Installation](#installation)
-   [Initalizing](#initalizing)
-   [Importing Data](#importing-data)
    * [Points](#points)
    * [Vectors](#vectors)
    * [Anatomical Axis](#anatomical-axis)
    * [Segment Center of Mass](#segment-center-of-mass)
    * [Total Body Center of Mass](#total-body-center-of-mass)
-   [Viewing and Controling the Visualization](#viewing-and-controling-the-visualization)
    * [3D Visualizer](#3d-visualizer)
    * [2D Visualizer](#2d-visualizer)
        - [Drag and Drop or Select Files Box](#drag-and-drop-or-select-files-box)
        - [Interactive Graph Selection for Time Series](#interactive-graph-selection-for-time-series)
-   [Contributing](#contributing)

## Installation

Installation can be performed with the requirements.txt file included in the project. Install dependencies with the following command in terminal:

```bash
pip install -r requirements.txt
```

## Initalizing

After installing the necessary dependencies, execute the program:

```
python plotDash.py
```

Note: Please ensure the terminal is currently set to the directory that contains the python script.  To do so, run cd "path to folder" ex: cd C:\Users\Name\Documents\BiomechOS

From here, you can select mat files to import into the project using the file selector.

Both 3D and 2D graphs can then be manipulated to analyze data.

## Importing Data

Upon running, the following window will appear.

![Alt text](imgs\file_loader.png)

Select Browse.  There are five mat files needed to run the program. Each mat file corresponds to one of the following: Points, Vectors, Anatomical Axis, Segment Center of Mass and Total Body Center of Mass.  ALL FIVE must be selected for the program to run.

The following sections describe the way each data type must be passed.

- ### Points

    Points are a list of dictonaries.  Each key is the point name and the value is an N x 3 matrix.  The three columns represent the X, Y and Z positive respecitively.  The row index represents the timestep for that point location

- ### Vectors

    IMPORTANT NOTE: Currently only one vector, name "TBCMVeloc" is supported.  This represents the Total Body Center of Mass Velocity vector

- ### Anatomical Axis

    Anatomical Axis is a list of dictonaries. The key is the Segment Center of Mass name to conenct the axis to.  The value is 3x3xN where the top N is the frame the axis comes from, the first nest is the three axis (x-axis, y-axis, z-axis) and the last nest is the location of the end point of the axis (x, y, z).  In the final graph, the x-axis is drawn red, the y-axis is drawn green and the z-axis is drawn blue for RGB.

- ### Segment Center of Mass

    Segment Center of Mass is a list of dictonaries.  Each key is the name of the segment.  Each value is a N x 3 matrix in the same form as all [points](#points).

- ### Total Body Center of Mass

    A single N x 3 matrix representing the total body center of mass.  The matrix is represented the same way as all [points](#points).

## Viewing and Controling the Visualization

Once the files have been selected, a local url will be displayed in the terminal.  

![Alt text](imgs\url.png)

Navigate to that url on any browser to view the GUI.

On the left half of the screen is the [3D Visualizer](#3d-visualizer) and on the right half is the [2D Visualizer](#2d-visualizer)

For either visualization, hover over a point to display information about it, such as position and name. 

- ### 3D Visualizer

    The 3D visualizer (shown below) is designed to view the 3D plots over time
   ![Alt text](imgs\3d.png)

    To rotate the camera, click and drag anywhere withing the plot.  To zoom, scroll in or out. When hovering over the graph, the icons in the top right can also be used to control the camera more precisely.  For more information about these icons, please see: https://plotly.com/chart-studio-help/getting-to-know-the-plotly-modebar/

    The Framerate input is the sub sampling rate.  If the framerate input is set to 10, every 10th frame will be drawn in the 3D plot.  This sampling will start from the current frame

    The Current Frame can be used to create a plot of a specific frame.  When set, the 3D plot will be redrawn with the first displayed image being the "Current frame".  The Current Frame also functions as the start frame.  The displayed 3D plot will not be able to go before the current frame.  When restarted, the plot will return to the frame set in Current Frame.

    The Frame Slider is also provided for control over the Current Frame.  When set, the Frame Slider will update the Current Frame with the value selected


- ### 2D Visualizer

    The 2D visualizer (shown below) has two tools.  The top is the [Drag and Drop or Select Files Box](#drag-and-drop-or-select-files-box)  The bottom is the [Interactive Graph Selection for Time Series](#interactive-graph-selection-for-time-series)
    ![Alt text](imgs\2d.png)

    - #### Drag and Drop or Select Files Box

        Selecting this box will open a new file explorer prompt.  Either select the five new files or drag them into the box to add this new trial to the data.  Again ALL FIVE files must be selected to add this trial.

    - #### Interactive Graph Selection for Time Series

        Select this box to add a time series plot. When clicked, the following prompt will appear.

        ![Alt text](imgs\time_series.png)

        The graph title, x axis label and y axis label can all be set in the first three boxes.  
        
        The height controls the total height (in pixels) of the visualization

        Use the leftmost dropdown to select the point to plot.  When the dropdown is clicked, you can type to search for the point name.  Point names are taken directly from imported data.

        Use the second dropdown to select which dimension of the point to plot.  You can plot the X, Y or Z.  This dimension will be plotted on the y axis over time or another point of data that you selected. If not point is selected for the X-axis, by default it will be time.

        The last box allows you to select the color of the line.

        Click "Add Another Line" to add another line on this 2D plot.

        At this time the "Customize Graph" button has not been implemented.

        Click "Remove Graph" to delete the above graph

        Note: You can add as many plots or lines to a single plot as you want.

        Note: When hovering over a graph, the icons in the top right can also be used to control the graph more precisely.  For more information about these icons, please see: https://plotly.com/chart-studio-help/getting-to-know-the-plotly-modebar/


## Contributing

If you want to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch (git checkout -b feature).
3. Make your changes.
4. Commit your changes (git commit -am 'Add new feature').
5. Push to the branch (git push origin feature).
6. Create a new Pull Request.