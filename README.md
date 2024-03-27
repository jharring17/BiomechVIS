# BiomechOS

Within the research space, there are few tools that can be leveraged by labs for data visualization and analysis. This often leaves researchers to create their own tool to visualize their data. With BiomechOS we hope to solve the problem of standardization of data visualization tools for lab settings. BiomechOS will be capable of receiving a variety of import data, creating time series graphs in 2D space, generating 3D visualizations using a point and line system, and allowing user interaction with the visualized data. This will allow researchers to effectively view their data and deepen their analysis.

## Table of Contents

-   [Installation](#installation)
-   [Usage](#usage)
-   [Contributing](#contributing)

## Installation

Installation can be performed with the bash script in the project. To run the script, enter the project directory execute the following command in terminal:

```bash
./dependencies.sh
```

Note: If the script requires permission changes to make it executable, run the following command in terminal:

```bash
chmod +x dependencies.sh
```

## Usage

After installing the necessary dependencies, execute the program:

```
python plotDash.py
```

From here, you can select mat files to import into the project using the file selector.

Both 3D and 2D graphs can then be manipulated to analyze data.

## Contributing

If you want to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch (git checkout -b feature).
3. Make your changes.
4. Commit your changes (git commit -am 'Add new feature').
5. Push to the branch (git push origin feature).
6. Create a new Pull Request.