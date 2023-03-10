from setuptools import setup

setup(
    name="some_gizmo_demos",
    install_requires=["H5Gizmos"],
    package_data={
        "some_gizmo_demos": [
            '*.css'
            ],
        },
    entry_points={
        "H5Gizmos.scripts": [
            "simple_todo = some_gizmo_demos.simple_todo:main",
            "hello_curves = some_gizmo_demos.hello_curves:main",
        ]
    },
)