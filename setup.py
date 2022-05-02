from setuptools import setup

url = "https://github.com/AaronWatters/H5Gizmos"
version = "0.1.4"
readme = open('README.md').read()

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
    long_description_content_type="text/markdown",
    include_package_data=True,
    author="Aaron Watters",
    author_email="awatters@flatironinstitute.org",
    url=url,
    install_requires=[
        "numpy",
        "aiohttp",
        "imageio",
        #"pyperclip", # must be installed manually if needed.
        #"ipython",  # You should only need this if you have it installed already???
        ],
    scripts = [
        "bin/snap_gizmo",
        "bin/gif_gizmo",
    ],
    package_data={
        "H5Gizmos": [
            'js/*.js'
            ],
        },
    python_requires=">=3.6",
)
