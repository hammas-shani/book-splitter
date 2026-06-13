# Book Splitter
================

## Project Overview
-----------------

The Book Splitter is a Python-based application designed to split large books into manageable chunks. This project utilizes a Docker container to ensure portability and reproducibility across various environments.

## Features
------------

*   **Book Splitting**: The application splits large books into smaller, more readable chunks based on a specified number of pages or words.
*   **Customizable**: Users can adjust the splitting criteria to suit their needs.
*   **Portable**: The application is containerized using Docker, making it easy to deploy on any system.

## Tech Stack
-------------

*   **Programming Language**: Python 3.x
*   **Containerization**: Docker
*   **Dependency Management**: pip

## Architecture
-------------

### High-Level Overview

The Book Splitter application consists of a single Python script (`app.py`) that performs the book splitting functionality. This script relies on the `requirements.txt` file to manage dependencies.

### Docker Container

The `Dockerfile` is used to create a Docker container that runs the Book Splitter application. The container is configured to use the `python:3.x` base image and copies the `app.py` script and `requirements.txt` file into the container.

### Build and Run

To build the Docker container, navigate to the project directory and run the following command:

```bash
docker build -t book-splitter .
```

To run the container, execute the following command:

```bash
docker run -it book-splitter
```

This will start the Book Splitter application, and it will be available on the default port (usually 8080).

## Requirements
------------

To run the Book Splitter application, you will need to have Docker installed on your system. Additionally, you will need to have Python 3.x and pip installed.

### Installation

To install the required dependencies, navigate to the project directory and run the following command:

```bash
pip install -r requirements.txt
```

### Usage

To use the Book Splitter application, simply run the Docker container using the `docker run` command. The application will be available on the default port (usually 8080).

### Example Use Case

To split a book into 10 chunks, you can use the following command:

```bash
docker run -it book-splitter --split-pages 10 <input_file>
```

Replace `<input_file>` with the path to the book file you want to split. The output will be written to the standard output.

### Contributing

Contributions to the Book Splitter project are welcome. To contribute, fork the repository, make changes to the code, and submit a pull request.

### License

The Book Splitter project is licensed under the MIT License. For more information, see the LICENSE file in the repository.