from setuptools import setup

url = "https://github.com/AaronWatters/H5Gizmos"
version = "0.1.8"
readme = open('README.md').read()

setup(
    name="H5Gizmos",
    packages=[
        "H5Gizmos", 
        "H5Gizmos.python",
        "H5Gizmos.python.test",
        "H5Gizmos.python.scripts",
        ],
    version=version,
    description="Tools for building interactive graphical interfaces for applications using browser technology and HTML5",
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
        'matplotlib>=2.0.0',
        'jupyter-server-proxy',
        #"pyperclip", # must be installed manually if needed.
        #"ipython",  # You should only need this if you have it installed already???
        ],
    scripts = [
        "bin/snap_gizmo",
        "bin/gif_gizmo",
        "bin/gizmo_link",
        "bin/gizmo_script",
        "bin/gz_examine",
        "bin/json_gizmo",
    ],
    package_data={
        "H5Gizmos": [
            'js/*.js'
            ],
        },
    python_requires=">=3.6",
    entry_points={
        'jupyter_serverproxy_servers': [
            'GizmoLink = H5Gizmos:setup_gizmo_link',
        ],
        "H5Gizmos.scripts": [
            "hello_env = H5Gizmos.python.scripts.hello_env:main",
            "Lorenz_Attractor = H5Gizmos.python.scripts.lorenz:main",
            "show_binary = H5Gizmos.python.scripts.show_binary:main",
        ]
    },
)
