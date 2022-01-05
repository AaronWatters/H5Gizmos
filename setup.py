from setuptools import setup

url = ""
version = "0.1.0"
readme = open('README.md').read()

# Note:  psutil is needed for demo purposes only.

setup(
    name="H5Gizmos",
    packages=[
        "H5Gizmos", 
        "H5Gizmos.python",
        "H5Gizmos.python.test",
        ],
    version=version,
    description="Tools for building simple interactive graphical interfaces for applications using browser technology and HTML5",
    long_description=readme,
    include_package_data=True,
    author="Aaron Watters",
    author_email="awatters@flatironinstitute.org",
    url=url,
    install_requires=[
        "numpy",
        "aiohttp",
        "imageio",
        "pyperclip",
        #"ipython",  # You should only need this if you have it installed already???
        ],
    scripts = [
        "bin/snap_gizmo",
    ],
    package_data={
        "H5Gizmos": [
            'js/*.js'
            ],
        },
)
